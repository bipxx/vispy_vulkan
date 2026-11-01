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
| Performance (W8) | Report done. Resident scenes keep the refresh rate; uploads are slower than OpenGL's, and partial texture updates much slower (B18). Readback presentation costs over 200 ms per 4K frame (B19). The hot swap moves to native presentation at R2, after the napari parity suites pass under it (D18). B19 and B18's CPU part are fixed on the R2 branch (run `b19-readback-257`). Full texture uploads are about 3 times faster there (P1). Vsynced native presentation there now paces like OpenGL's swap, without the extra refresh (P2). A texture updated between two draws of one frame no longer copies its whole CPU shadow (P3). A vsynced frame slower than a refresh renders one frame ahead, which brings full uploads to 0.82-0.99 of OpenGL's frame rate in a compact re-run (P4). Full uploads now copy straight from their CPU shadow (P5), and streamed buffers from their payload blocks (P6): in a compact re-run, a full 64 MiB image runs at 1.08 of OpenGL's frame rate, a 256-cubed volume at 1.08, and 1M points with new positions at 1.19. | `docs/performance-report.md` |

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
| D8 | **The four render-plane-scheduled cases stay failing and documented, with no new tolerance** (user, 2026-10-29). W5's wide-line fixes were tried first; this revises the user's earlier approval of a looser rule, which rested on a wrong diagnosis. **Revised under D19** (user, 2026-10-29: "Yes, apply it to D8 too"): the cases are judged by a correctly-positioned line criterion. The stroke pixels must be at the same places, with no gaps or stray pixels, and their intensity need not be exact. The criterion is fixed, with CPU negative controls, before the four cases are re-run. **They pass** (run `d8-positioned-255`, R2 test wheel). 8 to 14 pixels per case exceed 32 levels, by up to 104, and every one lies on a stroke edge in both frames. Alpha and interiors are exact. | On the minimum-coverage test wheel (run `w5-fringe-native-234`), 11, 11, 8 and 14 pixels per case still exceed the bound, by up to 104: GL's driver-defined smoothing of short 3D stroke segments (W5 findings). Earlier, 52-61 pixels per case exceeded the 32-level bound. A one-pixel boundary-move rule was fixed and tested before the re-run. It explained 33-46 of them and left 15-25, so all four cases still failed (run `w10-render-plane-rule-221`). Inspection then showed the pixels are not on the render plane's boundary, as first described. They are on napari-threedee's manipulator strokes, vispy `Line(width=3, method='gl')`. They were first described as aliased, but napari-threedee sets `antialias = 2` on them after construction, so they are smooth lines, drawn in 3D against spherical markers that write per-fragment depth. |
| D9 | **Mesh `axes_colorbar` closes with a documented difference.** Only for that scene, the smooth-line rule's 1% frame cap does not apply. Interiors stay exact, every other pixel stays within 32 levels, alpha matches exactly, and the fixture's landmarks match exactly. Implemented in `tools/mesh_layout_smooth_line.py`, with CPU negative controls. | With the 0.14 px line-end fix, the scene's worst pixel fell from 147 to 12 levels. 418 pixels still differed (1.17%, cap 1%). 332 of them are the 166-px axis line's two antialiased edge rows, 11-12 levels off: GL's driver-defined side coverage, which a simple renderer model does not reproduce. |
| D10 | **napari `tracks` and `shapes_selected` (W4, M11) close with a documented difference like D9** (user, 2026-10-29). For those two cases the 1% frame cap does not apply. Interiors stay exact, every pixel stays within 32 levels, alpha matches exactly, and the fixture's landmarks match exactly. Implemented in `tools/napari_vector_layers_comparison.py`, with CPU negative controls. | On the minimum-coverage test wheel, both fail only the frame cap: 2.7% and 3.7% of pixels differ, by at most 14 and 13 levels, with interiors and alpha exact. `shapes_selected` already passes this rule on `444402`; `tracks` needs the minimum coverage that lands with R2. |
| D11 | **W4 napari `colorbar` and `histogram` close with the documented difference of D9 and D10** (user, 2026-10-29). No 1% frame cap; interiors exact, every pixel within 32 levels, alpha exact. Implemented in `tools/napari_layer_families_comparison.py`, with CPU negative controls. | On the test wheel with R2's fixes, 1.5% and 3.2% of pixels differ, on the antialiased box, tick and axis lines, by at most 19 and 12 levels. |
| D12 | **W4 napari `surface_shaded` closes with an edge-pixel rule** (user, 2026-10-29). Interiors (uniform reference 3x3 neighbourhoods) stay exact, and at most 0.1% of the frame may differ, only on edge pixels, by any amount. Implemented in the same module, with CPU negative controls. | 7 of 49,152 pixels differ where the folded surface's front and back faces meet: OpenGL shows a single dark back-face pixel, and Dawn's matches its neighbours. Vertex-precision differences decide which face covers a near-tie pixel. |
| D13 | **H01's glFinish counts are recorded as evidence, not compared** (user, 2026-10-29). The screenshot after a layer removal stays exact, and "no hidden finish" means the harness never requests one. Implemented in `tools/napari_layer_controls_comparison.py`. | napari requests the same finishes in both renderers. OpenGL's `QOpenGLWidget.grabFramebuffer` synchronizes inside Qt, invisible to the command log; the Dawn readback logs the same synchronization as a `glFinish` (2 against 1). |
| D14 | **W5 napari `volume_iso` closes with a small shading rule** (user, 2026-10-29). Pixels whose reference 3x3 neighbourhood is uniform stay exact; at most 0.1% of the frame may differ, each by at most 4 levels. Same module, with CPU negative controls. | 1 of 19,200 pixels differs by 3 levels inside the shaded iso surface: float differences in the hit point or shading normal. The other volume controls match exactly. |
| D15 | **M08's smooth wide-line cases and the defined-depth case use the smooth-line rule without the frame cap, with exact alpha** (user, 2026-10-29). Aliased cases stay exact. This narrows D5's "everything else stays exact" for these two fixtures. Implemented in `tools/wide_lines_comparison.py`, with CPU negative controls. | On the test wheel with R2's fixes, five cases fail only the 1% cap, which is under 8 pixels in a 32x24 frame: 8-68 edge pixels differ, by at most 19 levels, with interiors and alpha exact. |
| D16 | **The wide-line reference tests pin both shared-fixture hashes** (user, 2026-10-29): the packets were captured with `tools/fixture_wide_lines.py` `f689a08a`, and the current fixture is `2568d76f`. | A reviewed publication on 2026-10-11 replaced the shared fixture, adding only the depth clear for `depth_occlusion_smooth`, and asked later source contexts to acknowledge it. The tests never did, so every reference check failed on the hash. |
| D17 | **Markers M02 and M06 close with a documented difference** (user, 2026-10-29, under D4), fixed in the new fixtures before their final capture. M02: uniform pixels exact; at most 0.1% of the frame may differ, only on edge pixels, by any amount. M06: at most 0.5% of pixels may differ by more than 2 levels; every other pixel within 2. | Measured with exact captures first: aliased markers flip 41 edge pixels at exact inside/outside ties on arrow, diamond and tailed_arrow, as in the original native63 failure. The `points` method differs by 1-2 levels on fractional sizes (OpenGL appears to quantize sprite size; truncating to 1/32 explains about 70%), and dense overlap cascades that into 0.24% of pixels. |
| D18 | **The hot swap presents through a native swapchain on Windows, from R2, once the napari parity suites pass under it** (user, 2026-10-29, under D3). GL activity that the audit attributes to a driver's presentation path, outside the renderer, counts as host activity, in the hot-swap profile only. Readback stays the strict no-OpenGL path and is made cheaper (B19). | W8 (`docs/performance-report.md`): at 3840x2160, readback paints are 226 ms apart for a resident image, native paints 2.3 ms. Readback costs about 53 ms per frame even at 1920x1080, and the design forbids interaction that depends on a CPU readback (:631). Stock napari passes both hot-swap gates under each presentation, with no driver GL activity observed. **Parity under native presentation: done** (runs `d18-native-parity-249` and `d8-positioned-255`, R2 test wheel). No test changes outcome between readback and native. Under both, the five in-process napari suites pass 44 of 44, the overlay workflows 5 of 5, the render-plane-scheduled suite 6 of 6 (under D19) and the plugin-wheel suite 5 of 5. Only D6's superseded fixtures fail, and they stop before rendering by design. |
| D19 | **Lines pass when they are correctly positioned and look right; exact pixels are not required** (user, 2026-10-29: "as long as the lines look correctly positioned and look elegant, then we should be good to go. no need to be exact"). This is a general rule. For W7, WSL lavapipe lines are judged against the admitted NVIDIA references under the smooth-line rule, and Mesa llvmpipe's own smooth-line rasterization is not used as a line oracle. D8 is revised under it. | W7's measurement (run `w7-lavapipe-smooth-254`). The port on lavapipe matches the NVIDIA references within 19 levels on every smooth-line frame. Against llvmpipe OpenGL, 15 of 29 frames exceed 32: line ends, a fringe row, a depth fringe and a missing 1/32 coverage skip, which llvmpipe also shows against NVIDIA. |
| D20 | **R1's instrumentation watches from outside the process** (user, 2026-10-29: "Out-of-process poller"). `tools/pool_watch_external.py` reads each watched process's handle table (`NtQueryInformationProcess`, `ProcessHandleInformation`). It follows the launched process tree through a job object without limits. Nothing runs inside napari, and no admin is needed. The in-process `tools/pool_watch.py` is no longer used. | The in-process watcher crashed 3 of 3 Tk test runs (run 257) and 2 of 3 runs of a plain Tk script (run 259). CPython 3.12 runs a scheduled collection in whichever thread next executes bytecode, so the watcher's thread ran Tk's finalizers. In run 259 the external watcher found the interpreter behind uv's launcher and recorded a real lost pool in a test child. It cost about 7% of a core during napari launches. |
| D21 | **Linux non-line frames are judged against Mesa llvmpipe OpenGL** (user, 2026-10-29: "Judge vs llvmpipe"), after checking that the port matches llvmpipe on the frames with the findings. Lines stay under D19. **Text frames are judged like lines, by D19's positioned-line rule** (user, 2026-10-29: "Treat text like lines (D19)"). | Run 254's captures, compared against llvmpipe: every interior pixel of every frame matches, and the hollow volume block and the text and overlay placement are identical. The remaining differences are on line edges (D19), on 5 edge pixels of `surface_shaded` (D12's rule), and on 2 pixels of `surface_wireframe`, a line frame, by 1 level. |
| D22 | **Native presentation under vsync paces like OpenGL's swap** (user, 2026-10-30: "Pace like OpenGL"). On a FIFO surface, the paint returns once its own frame's GPU work has retired. The wait is bounded, and counted as `present_pacing_waits` with its time and timeouts. W8's measured-work gate still forbids `completion_waits` and `finish_calls`. | Run `perf-profile-261`: the port let up to 3 frames queue ahead, so its frames retired one refresh after OpenGL's. Paced and pinned (D23), its median and p95 are 16.32 and 19.01 ms, against 33.09 and 35.52 without pacing and upstream's 16.62 and 33.45. Mailbox retired frames in 3.2 ms, but rendered 286 fps and showed 21% of them. Deferring paints would not show in W8's metric. |
| D23 | **On-screen benchmark runs keep every process on the performance cores** (user, 2026-10-30: "Run, pinned to fast cores"). Run `perf-profile-261`'s `pinned_launch.py` starts the run in a job object limited to the processors of the highest efficiency class, and opts each process out of power throttling. Each process's mask is recorded. Nothing system-wide changes. | Unpinned, Windows ran the non-foreground benchmark windows on efficiency cores in 60-66% of frames. Per-frame CPU work took 2-3 times as long, and refreshes were missed. The two wheels compared were identical headless and on screen. |
| D24 | **P3 as revised: copy-on-write copies a texture's CPU shadow only when it must** (user, 2026-10-30: "implement the design"). A settled revision, current on the GPU with nothing pending, moves its shadow to the copy. An entire update copies none. A device loss rebuilds a live revision from its own pixels. The first design's rule, update in place when only submitted frames hold the texture, is dropped. | Run `perf-profile-261`'s probes: after P2's pacing, and under readback, updates made before a frame's draws already reuse the texture, so the first design's case no longer occurs on napari's paths. Copy-on-write remained for an update between two draws of one frame, at about 20 ms per 64 MiB texture, almost all a shadow copy. |
| D25 | **A vsynced frame slower than a refresh renders one frame ahead** (user, 2026-10-31: "sure", to pacing on the previous frame so that CPU work overlaps the GPU, with camera-only latency kept at one refresh). D22 still holds for a frame produced in less than one refresh interval, counted from the previous paced paint's return: its paint returns once its own GPU work has retired. A slower frame's paint returns once the previous frame has retired. The Win32 surface reads its monitor's refresh rate, and elsewhere pacing assumes 60 Hz. | Runs `quick-bench-262` and `pacing-ahead-263`. With P1-P3, the paced paint waited 10.6-28.5 ms per heavy frame, which OpenGL overlaps with the next frame's CPU work: 0.64-0.72 of OpenGL's frame rate on uploads. Waiting only for the previous frame would show camera-only frames a refresh later, since they are produced faster than the display shows them. |
| D26 | **A full texture upload copies straight from its CPU shadow** (user, 2026-10-31: "Host import + fallback (Recommended)"). A payload snapshot of at least 1 MiB is captured into a pooled, page-aligned host block, which a full update makes the texture's CPU shadow. When the device has Dawn's experimental `HostMappedPointer` feature, which the `allow_unsafe_apis` instance toggle allows, a full upload that needs no conversion and whose rows are a multiple of 256 bytes copies from the block's import. Imports pin at most 512 MiB of host memory. Every other upload stages as before, and `VISPY_DAWN_HOST_IMPORT=0` turns imports and the toggle off. | Run `p5-upload-copies-265` (`p5-design.md`). A direct 64 MiB full upload made two CPU copies, the snapshot at flush and the staging copy, about 16 ms against OpenGL's 12.7. On this desktop, threads barely shorten a copy, which memory bandwidth bounds (7.6 to 5.7 ms). The toggle only allows extra APIs; nothing the port already uses changes. |
| D27 | **A streamed buffer copies straight from its payload block** (user, 2026-10-31: "continue", to "Import buffer uploads the same way, to cut the points' 11.4 ms buffer copy"). A whole buffer update with a payload of at least 1 MiB keeps the payload's host block as the buffer's bytes, and a revision whose size is a multiple of 4 bytes is copied on the GPU from the block's import before the render pass that reads it (D26's feature, toggle and 512 MiB limit). Vertex and index buffers of at least 1 MiB whose revisions have retired are reused by new revisions of the same size and usage. The batched draw routes and every other upload keep queue.WriteBuffer, and `VISPY_DAWN_HOST_IMPORT=0` turns imports off. | Run `p6-buffer-uploads-266`. napari 0.9.2 draws points as vispy's instanced markers (56 bytes per point; the port accepts its `use(gl='gl+')`), the route of the compact benchmark's points. A whole update copied the payload into the buffer's CPU shadow and again into Dawn's staging, and a buffer replaced while a frame read it allocated a new GPU buffer. |
| D28 | **Minor host changes are allowed, upstream first** (user, 2026-10-31: "I think it might be reasonable to allow some minor changes?"; 2026-11-01: "implemnt the plan", approving `2026-10-31-upstream-host-changes.md`). A host behaviour that needs a change outside vispy is fixed in this order: in vispy, which this project ships; upstream, in the host's own project, with the user's approval for each post (W12); or as a host patch used only by strict rows and registered in `compat/host-changes.json` with its upstream status. Hot-swap rows keep stock PyPI hosts; a row with a patched host is not a hot-swap row. A strict patch shrinks only at a requalification (R2 under D1), after a host release contains its upstream change. | Replacing only `vispy` is the hot swap's value. Patched hosts would need our own index (PyPI rejects local versions), re-patching for each host release, and a third profile. The two W12 changes are small: napari imports `OpenGL.error` lazily; qtpy imports Qt6's OpenGL modules lazily. Plan: `2026-10-31-upstream-host-changes.md`. |

No decisions are open. The latest is D28, upstream-first host changes.

The user has already decided, and confirmed on 2026-10-29, that the Windows
napari-threedee row stays required, so the release waits for R1. On 2026-10-29
the user also chose to finish the full plan (W4-W8 and the backlog) before R2.
W11 publication and W12 upstream posting each need explicit approval.

## Work items

### Release-critical

| ID | Work | Exit | Needs |
| --- | --- | --- | --- |
| R1 (W9) | Windows napari-threedee strict row | A cause and a regression test, then full lifecycle, nine-zero shutdown and all three gates on the release artifact (spec :340-345; status :86-87). A passing replay never closes it (diagnosis :49-50). | Identify the closer. Instrument hot-swap and diagnostic launches and wait for a recurrence. **Instrumentation** (2026-10-29): `tools/pool_watch.py` watches the default thread pool's worker-factory handle and, when it is lost, records the time, the handle's new type and every Python thread's stack. It only queries object types; CPU tests cover the record. Launches enable it with `VISPY_POOL_WATCH=<events.jsonl>`. **It crashes Tk processes** (run `b19-readback-257`): with it enabled, three of three Tk test runs ended in a fatal exception 0x80000003 in the watcher's thread while it was garbage-collecting; without it, none did. CPython 3.12 runs a scheduled collection in whichever thread next executes bytecode, so the watcher's 5 ms loop can run Tk's finalizers off Tk's thread, and Qt objects carry the same risk. It is replaced by an out-of-process watcher (D20, run `r1-external-poller-259`): `tools/pool_watch_external.py --output <events.jsonl> -- <command>` wraps a launch. Runs 249 and 255 made their napari launches without any watcher. |
| R2 | Release assembly: a fresh build of the then-current source (D1) | Every mandatory row requalified on it, final-head CI, promotion review | R1. The fresh source must include run `w4-napari-layer-families-236`'s patch set: run `w1-w5-native-batch-227`'s (W1, W5 smooth line ends, W15), run `w5-fringe-native-234`'s minimum smooth coverage, and the Qt backend's Dawn canvas release fix. Those are pinned runtime files, so the Tk candidate's runtime inputs are renewed with it. The patch set is kept, applied to `main`, on the branch `r2/pending-runtime-patches` (O5). D18 adds the switch of the Windows hot swap to native presentation, with strict no-OpenGL qualification selecting readback explicitly. It applies only after the napari parity suites pass under native presentation on the R2 test wheel. That condition is met (runs 249 and 255). The switch is made at R2 assembly, because selecting readback explicitly edits the pinned strict harness. The branch also carries B19 and B18's CPU part (run `b19-readback-257`) and P1's upload changes, P1's fix (step D), P2's pacing and P3 (run `perf-profile-261`), P4's render-ahead (run `pacing-ahead-263`), B20's fix (run `b20-staged-patch-264`), P5's host imports (run `p5-upload-copies-265`), and P6's buffer imports (run `p6-buffer-uploads-266`). Its head is `6435f6b`. |

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
| W3 | Hot-swap audit gates | Controls reached; the stock baseline passes | **Tooling done** (see Progress). The baseline's dynamic record is clean, but on `444402` its `renderer_gl` gate is UNVERIFIED because of one static GL reference in `gloo/glir.py`; it closes on the fresh build with W15. On the batch test wheel, which carries W15, stock napari reaches `PASS_HOT_SWAP_GATES`. W7 adds the Linux observer (run `w7-linux-observer-251`). D18 counts GL activity in a driver's native presentation path as host activity, in the hot-swap profile only. |
| W4 | napari families not yet covered: cyclic labels r8/r16, Shapes/Vectors/Tracks (M10, M11), Surface at napari level (a new fixture), overlays (E06, T04), histogram, sized export (Q03, Q06) | Each matches its OpenGL reference, or has a documented difference fixed before capture | Record results in `compat/vispy-compatibility.json`. **Fixtures done** (see Progress): every listed family has an OpenGL reference, and all pass on test wheels carrying R2's fixes (D10-D12). The matrix records them at R2. |
| W5 | Known defects: M02 and M06 markers, M08 wide lines (16 references; the depth failure is retained), M09 joins, caps and new line fixtures, B03 opacity mutation, H01 screenshot and layer removal with no hidden finish, V04 volume controls | Fixed and admitted. M02 and M06 close with a user-approved documented difference, fixed before re-capture (D4). | V07 and the plane widget belong to W10. V09 timing belongs to W8. M08 covers three residuals. Two are fixed in local test builds and ship with R2: the ends of smooth GL lines (W13 `scatter_axes`, W14 `axes_colorbar`), and the smooth-line fringe behind W4's `tracks` crossing (a minimum coverage, run 234). The third is napari-threedee's smooth 3D manipulator strokes in W10's four render-plane-scheduled cases, which pass under D19 (D8 revised). See W5 findings in Progress. **B03, H01 and V04 have fixtures and pass** (run 237, D13, D14). **M08 passes on the R2 test wheel** under D15 and D16 (run 239). **M09 passes exactly** on `444402` (run 241). **M02 and M06 pass under D17** on `444402` and the R2 test wheel (run 242). **Done**: every W5 item has a fixture and passes. |
| W6 | Hot-swap rows for PySide6 and CPython 3.11-3.14 | One row per cell passes W2 and W3 | Wheels for 3.10-3.14 exist only at an earlier epoch, so they must be rebuilt at the current source. Admissions use the 23-job CI and a promotion review. **Started** (see Progress): the PySide6 cp312 cell passes the probe's napari and threedee lifecycles. Its gates match PyQt6's, and both pass on the batch test wheel. The in-process scientific and plugin parity harnesses are PyQt6-only. **Local test wheels done** (2026-10-29, run `w6-abi-hot-swap-248`; the user chose local test builds now). CPython 3.11, 3.13 and 3.14 wheels were built from the R2 branch: the cp312 R2 test wheel with each ABI's two extension modules. All three pass the W3 gates and the probe's napari lifecycle; 3.11 and 3.13 also pass the threedee lifecycle. On 3.14 the threedee lifecycle is blocked upstream: napari-threedee 0.0.29 requires `zarr<3`, and zarr 2 needs a numcodecs older than 0.16, which has no 3.14 wheels. With zarr 3 forced, which fails `pip check`, it passes. Admission waits for R2's fresh build (D1). |
| W7 | WSL lavapipe hot-swap rows | WSL rows pass | Measure the smooth-line bound on lavapipe; 32 was measured on NVIDIA only. **Observer done** (2026-10-29; see Progress): a Linux hot-swap observer derived from the strict LD_AUDIT and ptrace pair. Its WSL native controls pass 20 of 20. **Linux rows done on a test wheel** (run `w7-linux-rows-253`), in WSL with lavapipe on Xvfb. The admitted `bd89a994` has the same `glir.py` PyOpenGL import as `444402`, so its stock napari row is UNVERIFIED, as on Windows. Test wheel A (`c5a3807d`) is `bd89a994` with R2's three Python files. On it, stock napari reaches `PASS_HOT_SWAP_GATES`, the three controls give their designed verdicts, and the probe's napari and threedee lifecycles pass. **Smooth-line measurement done** (run `w7-lavapipe-smooth-254`, wheel B `922867ce`: test wheel A with R2's native line change, 44/44 native contracts). The port on lavapipe stays within 19 levels of the NVIDIA references on every smooth-line frame. Mesa llvmpipe OpenGL differs from both, so D19 judges Linux lines against the NVIDIA references. Open Linux-only findings, shared by llvmpipe and lavapipe, which are not lines: the brightest volume block renders hollow, and napari text and overlays sit about 1 px off. **D21** (user, 2026-10-29) judges Linux non-line frames against llvmpipe. Run 254's captures show the port reproduces llvmpipe's hollow block and text placement exactly. Text frames are judged like lines (D21). Linux rows apply these rules when they are requalified at R2. |
| W8 (PERF-1) | Performance report: interaction frame time, large image and volume loads (including V09 timing), presentation path | A measured report against upstream OpenGL, with no speedup claim; the presentation choice is taken from the data (D3) | Native swapchain presentation is allowed only in hot swap. Inputs: the five-pair timings. PR #2 was closed, but its Qt single-present code is live (`src/vispy/app/backends/_qt.py:790-931`). Explain the unattributed Qt expose paints that invalidated the Native65 five-pair timing run (next-batch plan :443, :485, :3502). The pinned harness (`tools/benchmark_frames.py`) needs two environment settings: upstream PyQt6 canvases need `VISPY_PYQT5_SHARE_CONTEXT=true`, and only `VISPY_QT_PRESENTATION=native` reports the candidate completions it measures. It also passes `texture_format="rgba8"`, which VisPy expands to the invalid `rgbagba8`, so every RGBA workload fails on both sides. `tools/benchmark_frames_w8.py` runs the harness's code with those two lines fixed and the harness's hash recorded (O6). **Report done** (2026-10-29, run `w8-paced-benchmark-245`): [`docs/performance-report.md`](../../performance-report.md). Resident scenes keep the refresh rate, one refresh later than OpenGL. Full uploads run at about half OpenGL's rate. Partial texture updates run at 3.7 frames per second against 60 (B18). Readback presentation costs about 53 ms per frame at 1920x1080 and over 200 ms at 3840x2160 (B19). The unattributed paints come from desktop activity. Presentation: D18 (native for the hot swap from R2, after the napari parity suites pass under it). |
| W10 | Oracle fixtures: the threedee drag race; the render-plane fixtures, including V07 and the plane widget; the plugin plan's opaque-volume residual. In W2, 11 cases were blocked by unadmitted references in the threedee, initialized and render-plane suites. | Parity tests pass against new admitted oracle captures | New fixture modules and reference packets beside the retained ones, with an admission naming the oracle defect (D6). These suites draw manipulator lines, so they use the smooth-line criterion (D5). **Done on the R2 test wheel** (see Progress): the repaired fixtures exist and D5 is applied. The overlay suite passes 5 of 5, initialized `retirement` passes, and the render-plane-scheduled suite passes 6 of 6, its four manipulator cases under D19 (D8 revised; run `d8-positioned-255`). The superseded suites keep failing as documented (D6). This closes at R2. |
| W11 | Publication: GitHub Release plus a PEP 503 index with hashes, a manylinux build, and the 100 MiB wheel budget | A clean venv installs from the channel and the W2 smoke test passes | Only at the release, after R2 and approval; no preview (D2). Record a new artifact, and never replace the draft release's assets (gaps plan :581-582). Prepared locally (`tools/wheel_index.py`). |
| W12 | Upstream napari lazy `GLError` and qtpy lazy QtOpenGL | Upstream releases contain them | Approval. Drafts are in `docs/upstream-drafts/`. They remove the napari and qtpy patches, but stock Qt still fails the strict gates, so strict rows keep the Qt build without OpenGL. Under D28 (plan `2026-10-31-upstream-host-changes.md`). Each post needs approval; status in `compat/host-changes.json`. |
| W13 | Glue in hot swap: the five workflows (scatter, scatter edit, scatter axes, volume, volume edit) | All five pass with stock hosts | W3. `scatter_axes` uses the smooth-line criterion (D5; coverage H02). The design requires Glue (:26, :122), and no workstream covered it. **Partly done** (see Progress): 4 of 5 pass on `444402`. On the batch test wheel, which carries the smooth line end fix, all five pass, `scatter_axes` included, and the Glue scenario passes both hot-swap gates; this closes at R2. |
| W14 | Apply the smooth-line criterion to the mesh axes/colorbar scene and re-run it | It passes under the criterion | D5. Its fixture sources are pinned, so the criterion is added in new modules. **Partly done** (see Progress): 12 of 13 scenes pass on `444402`. On the batch test wheel all 13 pass, with `axes_colorbar` under its documented difference (D9); this closes at R2. |
| W15 | Remove upstream's PyOpenGL import from the shipped `gloo/glir.py`: `_check_pyopengl_3D()`, used only by the legacy GL `GlirParser`'s 3D textures | The W3 static scan finds no runtime GL reference, and the W3 stock baseline passes on the fresh build | R2. `glir.py` is pinned by the Tk candidate's runtime inputs, the DIVE PySide2 host environment and the Metal CI reuse record, so the edit lands with the fresh build. `GlirParser` stays public; its 3D-texture path now fails clearly instead. Validated on the batch test wheel: the static scan is clean, and stock napari passes both gates. |
| W16 | Hot-swap baseline on napari 0.10.0, PyPI's napari since 2026-10-30 (still `vispy>=0.17.0,<0.18`, `qtpy>=2.4.0`, `PyOpenGL>=3.1.10`) | On stock 0.10.0 with the current test wheel, every W2 case passes or has a recorded, triaged cause, and the stock scenario reaches `PASS_HOT_SWAP_GATES` | GUI runs need the user's go-ahead. Task 9 of `2026-10-31-upstream-host-changes.md`. |

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
| B18 | Partial texture updates copy the whole texture. `apply_texture_data` rebuilds the CPU shadow on every partial update. While a queued frame uses the texture, the update also copies the shadow once more and copies the texture into a new GPU texture. napari's labels painting makes such updates. W8 measured 3.7 frames per second against OpenGL's 60 for eight 64x64 patches per frame on 4096x4096 RGBA layers. The files are pinned runtime inputs, so the fix lands with R2 or later. **CPU part done on a test wheel** (2026-10-29, run `b19-readback-257`; on the R2 branch): a same-dtype patch is written into the shadow. Eight 64x64 patches per frame take 0.43 ms instead of 115.7 with the GPU idle, and 14.5 instead of 132.7 while a queued frame holds the texture. **Queued case** (P3, run `perf-profile-261`; on the R2 branch as `55fed04`): after P2's pacing, updates made before a frame's draws reuse the texture. An update between two draws of one frame moves the shadow instead of copying it: eight patches take 4.1 ms instead of 21.3. It still allocates a new GPU texture. | `docs/performance-report.md` (Partial texture updates) |
| B19 | Readback presentation's framebuffer read: about 23 ns per pixel natively (`read_canvas` allocates a staging buffer per read and converts each texel through a generic routine), then three Python copies (`_read_dawn_framebuffer`). That is about 53 ms per frame at 1920x1080. Pinned runtime files, as B18. **Done on a test wheel** (2026-10-29, run `b19-readback-257`; on the R2 branch). 8-bit RGBA and BGRA rows are copied, and the Qt path drops one Python copy. The bytes are identical. The whole Qt readback takes 8.2 ms at 1920x1080, down from 52.9, and 29.8 ms at 3840x2160, down from 218. The staging buffer is still allocated per read. | `docs/performance-report.md` (Readback presentation) |
| B20 | **A small staged texture patch could reach the GPU as zeros. Fixed on a test wheel** (run `b20-staged-patch-264`; on the R2 branch as `ffbd45a`). A frame copied a patch into its texture from a staging buffer that `queue.WriteBuffer` filled. When a new texture's first upload followed it in the same batch, that copy read zeros on the RTX 4090's Vulkan driver (610.88): the patch's texels stayed zero on the GPU, in that frame and later ones, while the CPU shadow was right. It needed a fresh process, and the new texture's upload and the patch's staging together had to stay under about 64 KiB; the patched texture's size did not matter. Uploading the new texture first, in an earlier frame, or the same bytes as a vertex buffer, avoided it. Dawn records the copy's write-to-read barrier as expected, so the driver is the likely cause; that is not proven. A revision's patches now stage through one host-mapped lease that the CPU fills, from a pool of their own, so the copy reads host memory. The pre-P1 wheel `9b7eea2d` had it, and labels painting could meet it. | Run `b20-staged-patch-264` (`b20_probe.py`, `tests/native/test_staged_patch.py`); run `perf-profile-261` (`p3_debug_variants.py`) |
| B21 | **Dawn aborts when a lost device is released while a host import was alive. Worked around** (run `p5-upload-copies-265`; on the R2 branch as `2946b54`). A `HostMappedPointer` buffer destroyed after its device is lost tracks its dispose callback as a queue task that never runs, so releasing the device fails `DAWN_CHECK(mTasksInFlight->Empty())`, which aborts the process silently in release builds. P5's imports carry no dispose callback, and the runtime decides when their pages may be freed: once a frame submitted after the release has retired, or once the device is destroyed. An upstream Dawn report would need approval, as W12 does. | Run `p5-upload-copies-265` (`probe/host_import_probe.cpp`, `probe-loss-*.txt`) |

### Organization (user, 2026-10-29)

| ID | Work | State |
| --- | --- | --- |
| O1 | Make drift between this working tree and published main visible | **Done.** `tools/publication_drift.py` compares every file of the publication clone's `origin/main` with the working tree, byte for byte, and lists changed (marking line-ending-only changes), missing and local-only files. A difference is explained only by the publication's own files (`--expect`) or by `KNOWN`, which records why a file stays local; anything else exits 1. Each publication runs it first. Its first run restored `main`'s bytes for two files whose local copies had lost their mixed line endings, and the missing `.gitattributes`. It also flagged two earlier-session notes: the 2026-10-23 scope note in the smooth-line mechanism plan and the 2026-10-22 Native63 notes in the coverage registry. The user chose to publish them after review (2026-10-29). Run `notes-publication-247` checked every claim against the linked local evidence (wheel, case names, pixel and pin counts; all hold). It marked stale wording as historical, and gave the 13 rows those notes rewrote their date, keeping `main`'s earlier text. |
| O2 | Mark the expected failures as expected | **Done, without xfail**, because the evidence rules forbid skip and xfail. `tests/hosts/conftest.py` and `tests/parity/conftest.py` label the listed failures in pytest's report and its JUnit XML: 37, all superseded oracle fixtures kept by D6. D8's four cases left the list when D19 revised D8. They count the failures the index does not explain and name any listed test that passes. No outcome changes. |
| O3 | One registry of the documented differences | **Done.** `tools/documented_outcomes.py` indexes D5, D9-D17 and D19: the modules that apply each decision, and the cases and limits they hold. It also holds the expected failures. A CPU contract checks it against those modules and against each suite's case list. |
| O4 | One curated contract entry instead of re-exports through an unrelated module | **Done.** `tests/contract/curated_contracts.py` lists the curated contract modules. Until R2 the wheel suite imports it; at R2, CI's list names it directly. Its check requires every contract module to run in a workflow, be curated, or be declared. It found 11 published CPU contract modules that run in no workflow (`NOT_IN_CI`); each joins the curated list after a run in CI's environment. `test_wheel_index` stays local until W11 (`UNPUBLISHED`), so the check allows a checkout without it. The first version listed it in `NOT_IN_CI`, which failed every CPU job of PR #38, because the published tree lacks it. The local CI-list run had passed on the local tree, which has it. |
| O5 | Keep the pending runtime patches outside `build/` | **Done.** Branch `r2/pending-runtime-patches` (`bfe66d3`, on `main` `f2f9129`) carries run 236's patch set, with only the replaced lines changed. `bdfce97` adds B19 and B18's CPU part (run `b19-readback-257`), and `8adcb25` adds P1's upload changes, `645b343` fixes their staged uploads, `53f3f49` adds P2's pacing, `55fed04` adds P3 (run `perf-profile-261`), `9c50894` adds P4 (run `pacing-ahead-263`), `ffbd45a` fixes B20 (run `b20-staged-patch-264`), `2946b54` adds P5 (run `p5-upload-copies-265`), and `6435f6b` adds P6 (run `p6-buffer-uploads-266`). It has no PR, and no workflow runs on it. R2 builds from it. |
| O6 | Line endings, and the benchmark harness's setup and format | **Done.** `main`'s `.gitattributes` (`* -text`) keeps checkouts byte-preserving, because dependency checksums and pinned file hashes need exact bytes, so mixed line endings are intentional and nothing is normalized; O1 flags line-ending-only drift instead. The pinned W8 harness is fixed in a successor (W8). |

### Performance (user, 2026-10-30)

The user asked to close the open work first, then look at performance, and chose this order.

| ID | Work | State |
| --- | --- | --- |
| P1 | Upload memory churn. Full uploads allocated and faulted in fresh memory every frame: the payload snapshot, the replaced CPU shadow, and Dawn's staging for `WriteTexture`. | **Textures done on a test wheel** (run `perf-profile-261`; on the R2 branch). Headless, with the upload every frame, a 4096x4096 float32 image takes 15.6 ms instead of 46.9 (64 fps instead of 21), and a 256-cubed volume 15.0 instead of 35.8. **Vertex buffers in part:** 60.3 ms instead of 106.6. Their uploads run inside the render pass, so reusing staging for them needs the draw encoder to upload before the pass begins (done in P6). W8's paced comparison has since been re-run in compact form (P4). **Fixed** (step D, `645b343`): C marked a staged upload current before Submit, so a frame whose encoding failed left the texture stale. |
| P2 | Frame latency. Native presentation shows each frame one refresh later than OpenGL (W8: 33 against 17 ms median). | **Done on a test wheel** (run `perf-profile-261`; on the R2 branch as `53f3f49`). The port let up to 3 frames queue ahead of the display. Under vsync it now paces like OpenGL's swap (D22): a median of 16.32 ms against upstream's 16.62, pinned (D23). **Open:** in this session the port, paced or not, missed 1-32 refreshes per 1,000 frames, in bursts of one every 5 frames for 2-3 s. W8, an earlier run and upstream show none. It looks like a presentation-timing effect of this desktop's mixed refresh rates. |
| P3 | B18's queued case: an update while a frame still holds the texture. | **Done on a test wheel** (run `perf-profile-261`, `p3-design.md`; on the R2 branch as `55fed04`). Revised design (D24): copy-on-write moves a settled revision's CPU shadow instead of copying it. On a 4096x4096 RGBA8 texture, between two draws, eight patches take 4.08 ms instead of 21.30, and a full upload 27.32 instead of 44.43. Single-draw frames are unchanged. Not done: pooling GPU textures, which would save about 3.5 ms per such frame for an extra 64 MiB of GPU memory. |
| P4 | Render-ahead. P2's paced paint waited for its own frame, so heavy frames ran their CPU and GPU work in series (run `quick-bench-262`: 0.64-0.72 of OpenGL's frame rate on full uploads). | **Done on a test wheel** (run `pacing-ahead-263`; on the R2 branch as `9c50894`). A frame that took at least one refresh to produce returns once the previous frame has retired (D25). In the same session as OpenGL: a full 64 MiB image upload at 29.5 against 34.2 fps, a 256-cubed volume at 30.4 against 37.0, and 1M points with new positions at 10.7 against 10.8. Camera-only frames still wait for their own (median 16.39 ms). What remained on uploads was CPU work: the payload snapshot and the staging copy, about 16 ms per 64 MiB image against OpenGL's 12.7 ms upload (P5). Run 263 reported 25.8 ms, counting the staging copy twice. |
| P5 | Upload copies. A direct full upload made two CPU copies: the payload snapshot at flush and the staging copy, about 16 ms per 64 MiB image against OpenGL's 12.7. | **Done on a test wheel** (run `p5-upload-copies-265`; on the R2 branch as `2946b54`). With D26, the GPU copies a full upload from its CPU shadow through a host import. In the same session as OpenGL, on screen: a full 64 MiB image at 43.3 against 39.9 fps, and a 256-cubed volume at 45.0 against 39.7. Camera-only frames and eight patches stay at 60 fps, and 1M points run at 11.0 against 11.3. The snapshot copy remains (7.3 ms on the image). Buffer uploads followed in P6. Not done: conversions such as RGB to RGBA into imported blocks. |
| P6 | Buffer uploads. A whole vertex buffer update copied its payload into the buffer's CPU shadow and again into Dawn's staging (the points' 11.4 ms buffer copy), and a buffer replaced while a frame read it allocated a new GPU buffer. | **Done on a test wheel** (run `p6-buffer-uploads-266`; on the R2 branch as `6435f6b`). With D27, a streamed buffer keeps its payload block as its bytes, and the GPU copies it from the block's import before the pass, into the GPU buffer of a retired revision. In the same session as OpenGL, on screen: 1M points with new positions at 12.75 against 10.74 fps (the port's paint 10.4 ms against 26.6), a full 64 MiB image at 42.5 against 39.2, and a 256-cubed volume at 43.2 against 39.8. The payload snapshot remains (8.2 ms on the points). Not done: the batched draw routes, which still upload in the pass. |

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

**P6 buffer uploads** on 2026-10-31, run `p6-buffer-uploads-266`, on the R2
branch.

- **Measurement.** napari 0.9.2 draws points as vispy's instanced markers: one
  interleaved buffer of 56 bytes per point, uploaded whole when the points
  change, the route of the compact benchmark's points. On 1M points the port
  took a payload snapshot at flush (7.5 ms), and native interpretation took
  18.9 ms: 11.4 in queue.WriteBuffer's copy into Dawn's staging, with its
  allocation, and most of the rest in a copy into the buffer's CPU shadow.
  With a frame in flight, each update also made a revision with a new 56 MB
  GPU buffer, a Vulkan allocation per frame.
- **Change** (D27, step L). A whole buffer update with a payload of at least
  1 MiB keeps the payload's host block as the buffer's bytes. A revision whose
  bytes are a block and whose size is a multiple of 4 is copied on the GPU
  from the block's import (P5's) before the render pass that reads it, and
  counts as uploaded once the frame is submitted, so a frame that fails to
  encode leaves it to upload again. Vertex and index buffers of at least
  1 MiB whose revisions died with a retired Ticket wait for eight more
  retirements, and a new revision of the same size and usage takes one. A
  patch of a revision that a frame still holds copies it into a pooled
  block. The batched draw routes and every other upload keep
  queue.WriteBuffer.
- **Checks.** A new test, `tests/native/test_buffer_import.py` (8 cases),
  fails all 8 on the K2 wheel, on the new counters (every pixel check passes
  there), and passes all 8 on L. ctest 44 of 44. The GPU test directories
  pass 1,701 of 1,894 (K2: 1,692 of 1,886): the new tests, and Tk start-up
  flakes, which pass when rerun. The benchmark tests pass 609 of 626 on both
  wheels, and the six napari parity suites 61 of 61.
- **Cost** (`p6_cost.py`, pinned, alternating with the K2 wheel in one
  session). Streaming one million instanced markers every frame takes
  11.2 ms per frame with a frame in flight (K2: 43.6), 18.1 updating in place
  (40.4) and 19.3 between two draws (51.3). The buffer copy, 12.5-14.9 ms on
  K2, is gone, and so are its 1-2 Vulkan allocations per frame.
- **Compact benchmark** (pinned, vsync, OpenGL in the same session). 1M
  points with new positions run at 12.75 against 10.74 fps (run 265: 11.0
  against 11.3); the port's paint takes 10.4 ms against OpenGL's 26.6, and
  native interpretation fell from 18.9 to 0.85 ms. A full 64 MiB image runs
  at 42.5 against 39.2, a 256-cubed volume at 43.2 against 39.8, and
  camera-only frames and eight patches stay at 60 fps. The payload snapshot
  remains (8.2 ms on the points).
- **On the R2 branch** as `6435f6b` (steps Lt and L).

**P5 upload copies** on 2026-10-31, run `p5-upload-copies-265`, on the R2
branch.

- **Correction.** Run 263 reported 25.8 ms of packing, interpretation and
  staging per 64 MiB image, but the staging copy is timed inside native
  interpretation, so that figure counted it twice. A direct full upload
  made two CPU copies: the payload snapshot at flush (about 7-8 ms) and the
  staging copy (about 7-9 ms), against OpenGL's 12.7 ms upload. Rows that
  are not a multiple of 256 bytes added a padded copy before staging.
- **Probe** (`probe/host_import_probe.cpp`). Threads only took a 64 MiB copy
  from 7.6 to 5.7 ms here, since memory bandwidth bounds it. Dawn's
  experimental `HostMappedPointer` works on the RTX 4090 (driver 610.88,
  4 KiB alignment): a texture copied from host memory held exactly the bytes
  the CPU wrote, and importing 64 MiB took about 1.5 ms. A fresh allocation
  per frame costs about 20 ms in page faults, so blocks are pooled. Vulkan
  still needs 256-byte rows for buffer copies.
- **Change** (D26, step K). A payload snapshot of at least 1 MiB goes into a
  pooled, 64 KiB-aligned host block, which a full update makes the CPU
  shadow. A direct full upload with 256-byte rows copies from the block's
  import, created on first use and kept while the block lives. The frame
  holds the block until its copy has retired, and a patch copies a block
  that a frame still holds instead of writing it. Imports pin at most
  512 MiB, releasing idle ones first (step K2 keeps that limit on existing
  imports too). Every other upload stages as before, and a pooled lease now
  takes padded rows as it copies them. `VISPY_DAWN_HOST_IMPORT=0` turns
  imports and the `allow_unsafe_apis` toggle off.
- **Dawn finding** (B21). A host import still alive when the device was
  lost made the process abort once the lost device was released. Imports
  carry no Dawn dispose callback, and the runtime decides when their pages
  may be freed: after a frame submitted later has retired (Dawn frees the
  import before that frame's completion callback), or once the device is
  destroyed.
- **Checks.** A new test, `tests/native/test_host_import.py` (8 cases),
  fails 7 cases on the J wheel and passes all 8 on K2, with new CPU contract
  cases for the blocks. ctest 44 of 44. The GPU test directories pass
  1,692 of 1,886 (J: 1,684 of 1,878): the new tests, and Tk start-up flakes,
  which pass when rerun. The benchmark tests pass 609 of 626 on both
  wheels, and the six napari parity suites 61 of 61.
- **Cost** (`p3_cost.py`, pinned, alternating with the J wheel in one
  session). A 4096x4096 RGBA8 full upload takes 12.8 ms per frame (J: 24.0),
  and 14.7 between two draws (J: 27.3); its staging copy, 8.3-11.6 ms on J,
  is gone. Eight patches take 0.55 ms (J: 0.58). This session's copies ran
  slower than run 264's (J's full upload: 12.7 ms there).
- **Compact benchmark** (pinned, vsync, OpenGL in the same session). A full
  64 MiB image runs at 43.3 against 39.9 fps, and a 256-cubed volume at 45.0
  against 39.7 (run 263: 0.86 and 0.82 of OpenGL). Camera-only frames and
  eight patches stay at 60 fps, and 1M points run at 11.0 against 11.3. On
  the image, the port's paint takes 9.2 ms against OpenGL's 11.8; native
  interpretation fell from 9.3 to 0.75 ms. The snapshot copy remains
  (7.3 ms), and on the points so does an 11.4 ms buffer copy.
- **On the R2 branch** as `2946b54` (steps Kt, Kt2, K and K2).

**B20 staged patches** on 2026-10-31, run `b20-staged-patch-264`, on the R2
branch.

- **Reproduction** (user, 2026-10-31: "conitnue", to "Should I start on
  B20?"). It shows only in a fresh process: run 261's single variants
  failed, and its sequences of variants passed. On the H wheel, a texture
  patch not yet uploaded, a draw, then a new texture's first upload in the
  same batch leave zeros in the patch's region on the GPU, in that frame
  and in later ones, while the CPU shadow is right.
- **Trigger.** The patched texture's size does not matter (32x32 to
  128x128), nor do the new texture's contents. The new texture's upload
  and the patch's staging together must stay under about 64 KiB: with a
  2 KiB patch, a 124x124 upload fails and a 125x125 one passes; with an
  8 KiB patch, 116x116 fails and 118x118 passes. Uploading the new
  texture before the patch, or in an earlier frame, avoids it, as does
  the same bytes as a vertex buffer. A fresh vertex buffer written before
  the new texture keeps its contents.
- **Cause.** The frame's copy reads the patch's staging buffer, which
  `queue.WriteBuffer` filled through Dawn's staging ring. Dawn records
  that fill, the copy and the write-to-read barrier between them as
  expected (code inspection), and the runtime's trace is the same for a
  failing and a passing size, so the NVIDIA driver (610.88) is the likely
  cause. That is not proven.
- **Fix** (step J). A revision's patches stage through one host-mapped
  lease that the CPU fills, so the copy reads host memory. The leases
  come from a pool of their own (powers of two from 64 KiB, at most 8
  kept, 64 MiB), so patches never take a full upload's lease.
- **Checks.** The new test, `tests/native/test_staged_patch.py`, runs
  each case in a child interpreter; it fails on the H wheel and passes
  on J, as does every probe case that failed on H. ctest 44 of 44. The GPU
  test directories pass 1,684 of 1,878 (H: 1,681 of 1,875): the new tests,
  and Tk start-up flakes. The benchmark tests pass 609 of 626 on both
  wheels, and the six napari parity suites 61 of 61.
- **Cost** (`p3_cost.py`, pinned). Eight 64x64 patches before one draw
  take 0.48 ms (H: 0.53), and between two draws 2.78 (H: 2.81). Buffer
  allocations drop from 8 to 0 per frame, with no Vulkan memory
  allocations.
- **On the R2 branch** as `ffbd45a` (steps Jt and J).

**P4 render-ahead** on 2026-10-31, runs `quick-bench-262` and
`pacing-ahead-263`, on the R2 branch.

- **Compact benchmark** (user, 2026-10-30: "can we have some more compact
  benchmark?"). Run 262's `quick_bench.py` wraps W8's paced harness: 50
  warm-up and 300 measured frames, 3 alternating pairs, and 1920x1080 image
  viewports, so every window stays on the primary monitor. It is pinned
  (D23) and takes 8-13 minutes. It is indicative, not PERF-1 qualification.
- **Cause.** With P1-P3 (run 262), the candidate kept up on camera-only
  frames and eight patches, but reached 0.64-0.72 of OpenGL's frame rate on
  full uploads. Its CPU work per frame was close to OpenGL's for the image
  and the points. The paced paint then waited 10.6-28.5 ms for its own
  frame, which OpenGL overlaps with the next frame's CPU work.
- **Fix** (D25, step H). A frame that took at least one refresh interval to
  produce returns once the previous frame has retired; a faster one still
  waits for its own. The Win32 surface reads its monitor's refresh rate. New
  counters `present_render_ahead` and `present_render_ahead_waits`, and a
  test override of the interval.
- **Result** (run 263, upstream against candidate fps): camera-only image
  60.0 and 60.0, with a candidate median of 16.39 ms; full 64 MiB image 34.2
  and 29.5 (run 262: 37.4 and 24.7); eight patches 60.0 and 60.0; 256-cubed
  volume 37.0 and 30.4; 1M points 10.8 and 10.7 (10.6 and 7.6). Every upload
  frame rendered ahead, and the candidate's frame time equals its CPU work.
- **Correction.** Run 262's volume rows ran about half as fast on both
  renderers as in run 263, and so did its first points pair. In run 263 the
  candidate's volume costs per byte match its image's, so there is no
  volume-specific upload cost.
- **Latency.** The harness now observes a heavy frame's completion when the
  next frame polls for it, as it does for upstream. Those latencies read
  higher than the GPU's retirement on both renderers, so frame rate is the
  measure there.
- **Checks.** ctest 44 of 44. A new Qt test: a frame slower than a refresh
  returns with at most one frame in flight, and fast frames still wait for
  their own. The pacing tests pass 8 of 8 runs. The GPU test directories
  pass 1,681 of 1,875 (ABCDEFG: 1,680 of 1,874), and only Tk start-up
  flakes differ. The benchmark tests pass 609 of 626 on both wheels.
- **Test fix** (step Ht). P2's unpaced test flushed 12 headless frames
  without processing events, and failed in 3 of 8 runs on ABCDEFG too
  ("submission capacity exhausted"). It now waits for a free frame slot.
- **On the R2 branch** as `9c50894` (steps H and Ht).

**P3 copy-on-write** on 2026-10-30, run `perf-profile-261`, on the R2 branch.

- **Premise checked after P2.** Small Qt canvases updated a 4096x4096
  RGBA8 texture every frame. Updates made before the frame's draws reused
  the texture, with 0 allocations per frame, under paced native, unpaced
  native and readback presentation. Copy-on-write remained only for an
  update between two draws of one frame. That cost about 20 ms per frame,
  almost all a copy of the 64 MiB CPU shadow, discarded at once for a full
  upload.
- **Revised design** (D24). A settled revision moves its shadow to the
  copy, an entire update copies none, a rejected update returns a moved
  shadow, and a device loss rebuilds a live revision from its own pixels.
  A whole-buffer update copies none of the old bytes. New probe counters
  show each path.
- **Result**, headless, pinned, frame median:
  - eight 64x64 patches between two draws: 21.30 to 4.08 ms;
  - a full upload between two draws: 44.43 to 27.32 ms;
  - single-draw frames unchanged.
- **Checks.** ctest 44 of 44. The GPU test directories pass 1,680 of 1,874
  (E: 1,672 of 1,866), and only Tk start-up flakes differ. The benchmark
  tests pass 609 of 626 on both wheels, and the six napari parity suites
  61 of 61. The eight new tests pass, and the
  device-loss one fails without the rebuild change.
- **On the R2 branch** as `55fed04` (steps F, Ft, Fu and G).
- **Found:** B20, a small staged patch that reaches the GPU as zeros. It
  predates P1 and is independent of copy-on-write.

**P2 frame latency** on 2026-10-30, run `perf-profile-261`, on the R2 branch.

- **Cause.** The port's paint returned at once, so W8's harness kept up to 3
  frames issued and not yet retired; 1-3 were in flight after each paint.
  Dawn's Vulkan FIFO swapchain asks for 2 images, so a frame retired two
  refreshes after its request. Upstream's next frame waits for its own swap.
- **Experiments** on W8's points workload, port median against upstream's:
  - as shipped: 32.9 against 16.6 ms;
  - one frame in flight (queue depth 1): 16.1 against 16.5 ms;
  - Mailbox: 3.2 ms, but 286 fps rendered and 21% of them shown.
- **Machine state.** In one campaign the port's processes ran 2-3 times
  slower and missed refreshes. Windows had put the non-foreground windows on
  efficiency cores (60-66% of frames). The wheels were identical headless
  and on screen. Hence D23.
- **Fix** (D22, step E). Under vsync, the paint returns once its own
  frame's GPU work has retired. The wait is counted as `present_pacing_waits`.
- **Confirmation**, pinned (D23), median and p95:
  - port, paced: 16.32 and 19.01 ms;
  - port, not paced: 33.09 and 35.52 ms;
  - upstream: 16.62 and 33.45 ms.

  Every measured frame paced, with no timeouts.
- **Checks.**
  - ctest 44 of 44.
  - A new Qt test: a vsynced paint returns with no frame in flight, and
    unpaced and headless frames do not wait.
  - The GPU test directories pass 1,672 of 1,866.
  - The benchmark tests pass 609 of 626 on both wheels.
  - Only Tk start-up flakes differ.
- **Step D**, a bug in P1's step C found while designing P3. A staged full
  upload was marked current before Submit, so a frame whose encoder was never
  submitted left the texture stale. Staged copies now commit after Submit.
  The ticket also holds every texture it uploads, which closes an older
  raw-pointer use-after-free. A new test fails with C and passes both before
  C and with D.
- **On the R2 branch** as `645b343` (D) and `53f3f49` (E). The first push of
  D got a GitHub server error, and one retry succeeded.
- **Open.** In this session the port, paced or not, missed 1-32 refreshes
  per 1,000 frames, even pinned. They came in bursts of one every 5 frames
  for 2-3 s. W8, an earlier run and upstream show none. It looks like a
  presentation-timing effect of this desktop's mixed refresh rates (the
  primary at 59 Hz, the others at 60 Hz).
- **P3's design** is written (`p3-design.md`) and waits for the user's review.

**P1 upload memory churn** on 2026-10-30, run `perf-profile-261`, on the R2
branch's tree (`bdfce97`).

- **Measured first.** Headless, every frame, on test wheel `9b7eea2d`:
  - A 64 MiB copy into fresh memory takes 12.3 ms; into reused memory, 5.6 ms.
    Page faults dominated.
  - The payload snapshot faulted in a new 64 MiB block.
  - The replaced CPU shadow was freed.
  - `WriteTexture` made Dawn allocate a dedicated staging buffer.
  - Structured vertex arrays took the legacy path, which copied them twice.
- **Changes.**
  - A: owned capture for structured and void dtypes.
  - B: a bounded native recycler for large byte blocks.
  - C: pooled host-mapped staging for full texture uploads, copied by the
    frame's own encoder.

  | Workload, every frame | Before | A+B | A+B+C |
  | --- | --- | --- | --- |
  | 4096x4096 float32 image | 46.9 ms | 25.4 ms | 15.6 ms |
  | 256-cubed float32 volume | 35.8 ms | 22.0 ms | 15.0 ms |
  | 56 MB vertex buffer, points | 106.6 ms | 62.7 ms | 60.3 ms |

- **Checks.**
  - ctest 44 of 44, with contracts for A and B.
  - A new GPU test for C checks every upload's bytes, and that warm uploads
    allocate nothing of their own.
  - The six GPU test directories pass 1,669 of 1,863 on both wheels. Only
    the new test and transient Tk start-up failures differ, and those pass
    on recheck.
  - napari parity passes 61 of 61.
- **On the R2 branch** as `8adcb25`.
- **Incident.** Two `uv run` calls from inside the snapshot created a stray,
  empty `.venv` there. It was removed before any build (standing rule).

**D20's out-of-process watcher** on 2026-10-29, run `r1-external-poller-259`.

- **Tool.** `tools/pool_watch_external.py` launches a command suspended,
  assigns it to a job object without limits, resumes it, and adopts each new
  job member. It reads each process's handle table every 5 ms, which takes
  microseconds. A first version enumerated all processes instead and watched
  only uv's launcher, not the interpreter it starts: process enumeration costs
  35-45 ms per look on this desktop.
- **Contract tests.** Six, including two live ones on Windows. One child
  closes its own default pool's handle and lets a semaphore take the value;
  the watcher records the loss. Off Windows, the tool records that it is
  unsupported and returns the command's exit code.
- **napari.** Three stock napari launches on the R2 test wheel exit 0. The
  watcher adopts the interpreter, records no loss, and uses 0.44-0.56 CPU
  seconds per 7 s launch.
- **Tk.** A plain Tk script that churns objects in reference cycles beside a
  busy thread crashed 2 of 3 runs with the in-process watcher (0x80000003 in
  its thread, garbage-collecting). Under the external watcher it completed 3
  of 3.

**B19 and B18's CPU part on a test wheel** on 2026-10-29, run
`b19-readback-257`, from the R2 branch's tree. Test wheel `9b7eea2d` is the
R2 test wheel with the new native module and two Python files.

- **Patches.**
  - `read_canvas` copies, swizzles or strips 8-bit RGBA and BGRA color rows.
    The old per-texel conversion gives back every byte unchanged, and a native
    contract compares the two for every byte value in every channel position.
  - The Qt readback path skips `read_pixels`' copy of the native array.
  - `apply_texture_data` writes a same-dtype patch into the resident shadow. A
    native contract requires it to keep the shadow's buffer.
  - ctest passes 44 of 44.
- **Measured against the R2 test wheel** on hidden or headless canvases, with
  identical bytes and final images:

  | Workload | Before | After |
  | --- | --- | --- |
  | Native read, 1920x1080 | 47.6 ms | 4.2 ms |
  | Native read, 3840x2160 | 198 ms | 15.8 ms |
  | Whole Qt readback, 1920x1080 | 52.9 ms | 8.2 ms |
  | Whole Qt readback, 3840x2160 | 218 ms | 29.8 ms |
  | Partial updates, GPU idle | 115.7 ms | 0.43 ms |
  | Partial updates, queued frame | 132.7 ms | 14.5 ms |

  Partial updates are eight 64x64 patches per frame on a 4096x4096 RGBA
  texture.
- **GPU tests.** Six test directories, 1,861 tests, were run on both wheels.
  Only the new readback test and two Tk tests differ. Those Tk tests failed at
  Tk start-up: Tcl transiently could not read its own library files, and which
  Tk tests fail varies between identical runs on one wheel.
- **napari parity.** Five in-process suites plus image extensions, 61 tests,
  pass 60 of 61, including `labels_paint_tile`, napari's partial-update path.
  The exception, `shapes_selected`, follows napari's saved settings rather
  than the wheel:
  - the wheel passes with a fresh `NAPARI_CONFIG`;
  - the R2 test wheel fails with a copy of the failing environment's settings
    (window at 0,0, 640x704).

  Its fixture sets the selection highlight before fixing the canvas size, so
  the saved window size moves the handles. An earlier attempt failed only
  because the environment lacked numba, which run 249's had.
- **R1 watcher.** It crashes Tk processes (see R1).
- **On the R2 branch** as `bdfce97`.

**Retention records** on 2026-10-29, run `d8-positioned-255`, after PR #42
merged (`d00b10f`; merged tree == tested tree, 11/11 required checks).

- **Found.** In 23 earlier runs, 50 retained files no longer match their terminal
  manifest. There are two causes:
  - in 4 runs, the PR check watch kept appending to its log in the run folder
    after the manifest was written, while non-required macOS jobs ran;
  - 46 files were main-tree files retained by path, which later work edited.
- **Located.** For 47 of them the retained bytes still exist: 4 as a prefix of
  the current log, 41 as a blob on `main` (one with its line endings
  converted), and 2 as a renamed copy in the run's folder. Three intermediate
  local versions from superseded runs 203 and 208 are lost.
- **Recorded.** The run's `retention-drift.json` lists every file. The 19
  affected runs of this work have a `retention-addendum.json`; four runs of
  other owners are listed there only. No terminal manifest was edited. Run 255's
  own first manifest hashed its retain log before the script wrote to it, and
  was replaced before any cleanup plan read it.
- **Rule.** Two hygiene standing rules prevent both causes.

**D8 under D19** on 2026-10-29, run `d8-positioned-255`: the four
render-plane-scheduled cases, judged by the positioned-line rule.

- **Rule.** `tools/positioned_line_comparison.py` was fixed before the re-run;
  `protocol.json` holds its sha256. It is the smooth-line criterion plus one
  allowance: a pixel beyond the 32-level edge bound passes when it lies on an
  edge in both frames, at most 0.1% of the frame. Interiors and alpha stay exact.
  Fifteen CPU negative controls show that a gap, a stray block, a shift, an
  interior or alpha change, and widespread differences fail, while a different
  intensity on the stroke passes.
- **Re-run.** It ran in a `git archive` copy, as in run 249, on the R2 test wheel.
  Two attempts compared nothing, and both are kept:
  - attempt 1: the copy lacked one of 51 gitignored input records in
    `compat/host-environments`;
  - attempt 2: the candidate had NumPy 2.5.3, which removed napari-threedee's
    `np.row_stack`. The suite pins 2.4.6.

  Attempt 3, with run 221's NumPy 2.4.6 lock, passes all six tests. The four
  cases have 204, 200, 236 and 204 differing pixels; 11, 14, 8 and 11 of them
  exceed 32, by at most 104, 92, 81 and 104.
- **Index.** `tools/documented_outcomes.py` drops D8's four expected failures
  (37 remain, all D6) and adds D19's rule. The wheel suite's D5 contract accepts
  the positioned rule for the scheduled suite only.

**W7 lavapipe smooth-line measurement** on 2026-10-29, run
`w7-lavapipe-smooth-254`, done by an implementation agent. I checked its
numbers against `results.json`.

- **Wheel B.** `922867ce` is test wheel A with `_dawn` rebuilt from the R2 branch
  in fresh mode. It passes 44 of 44 native contracts on lavapipe.
- **Protocol.** It was written and hashed before any capture. One amendment,
  also made before capture: the upstream file pins in
  `compat/upstream_manifest.json` are CRLF bytes, but the Linux vispy 0.17.0
  wheel installs them with LF, so the pins are checked after line-ending
  normalization.
- **Captures.** 46 cases on each side, under Mesa 25.2.8 llvmpipe OpenGL and
  lavapipe, on Xvfb. Repeat captures are byte-identical.
- **Results**, as edge maximum and frames over 32 for three comparisons: A,
  lavapipe against llvmpipe; B, lavapipe against the NVIDIA packets; C,
  llvmpipe against NVIDIA.

  | Fixture | A | B | C |
  | --- | --- | --- | --- |
  | Threedee overlay | 26, 0/8 | 255, 7/8 | 255, 7/8 |
  | Wide lines | 255, 10/13 | 19, 0/12 | 103, 9/12 |
  | Wide-line depth | 255, 1/1 | 1, 0/1 | 255, 1/1 |
  | Vector layers | 224, 1/2 | 14, 0/2 | 224, 1/2 |
  | Layer families | 45, 2/3 | 255, 2/3 | 255, 2/3 |
  | Mesh axes/colorbar | 145, 1/1 | 11, 0/1 | 147, 1/1 |

  - Every over-32 frame in A comes from llvmpipe differing from NVIDIA: line
    ends 128 where NVIDIA gives 164 and the port 163, a fringe row, a depth
    fringe, and a missing 1/32 coverage skip.
  - B's 255s on the overlay, scale bar and colorbar are not lines. They lie
    where both Linux renderers agree: the brightest volume block renders
    hollow, and napari text and overlays sit about 1 px off. These are open
    Linux findings.
  - The clipping bug affects no case.
- **Decision.** The user decided D19: lines pass when correctly positioned,
  without exact pixels. Linux lines are judged against the NVIDIA references.
- **Tool.** `tools/smooth_line_lavapipe_measurement.py`, with CPU tests.

**W7 Linux rows** on 2026-10-29, run `w7-linux-rows-253`: done by an
implementation agent, and the verdicts and the wheel were checked before this
record.

- **Lock.** The PyQt6 napari input, compiled for `x86_64-manylinux_2_39` with W6's
  flags and cutoff. Against W3's Windows lock it adds pexpect and ptyprocess and
  drops colorama, pywin32 and tzdata; the other 111 pins match.
- **Wheels.** The admitted `bd89a994`, and test wheel A (`c5a3807d`). Test wheel A
  is `bd89a994` with only `_qt.py`, `dawn_parser.py` and `glir.py` replaced by
  the R2 test wheel's. Every other member is byte-identical, and bd89's Python
  equals `444402`'s.
- **Gates** (Linux observer, lavapipe, Xvfb). All eight rows match their expected
  verdicts. Stock napari is UNVERIFIED on `bd89a994`: the static scan finds
  `glir.py`'s PyOpenGL import. On test wheel A it reaches
  `PASS_HOT_SWAP_GATES`.
- **Linux differences that change no verdict.**
  - The GL-context control stops at `glXCreatePbuffer` from Qt's GLX
    integration.
  - Stock napari records 80 host GL events, against 24 on Windows, because
    `libQt6Gui` links `libGL` and `libEGL` directly.
- **Probe.** On test wheel A, the napari lifecycle passes all 9 stages and the
  threedee lifecycle all 8.
- **Cleanup.** The guest scratch held `uv venv`'s symlinks. An audited unlink
  removed only those 8 links before both cleanups.

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
  - The overlay suite's five plugin workflows pass.
  - **Correction** (run `d8-positioned-255`). This entry first said the plugin
    suites failed only their 17 documented cases. That holds by node id, but six
    of them never rendered:
    - 11 of the 17 stop before rendering by design: D6's superseded fixtures,
      whose references are unadmitted;
    - D8's four cases and two D6 render-plane cases could not start their
      worker. The copy lacked a gitignored input record, and this run's
      NumPy 2.5.3 candidate lacks napari-threedee's `np.row_stack`; the suites
      pin 2.4.6.

    Run 255 completed the check with the NumPy 2.4.6 candidate.
    - The render-plane-scheduled suite passes 6 of 6 under both presentations,
      under D19.
    - The plugin-wheel suite passes 5 of 5 under both, run in the main tree
      with its evidence in scratch.
  - Four CPU tests failed in the copy, for missing untracked inputs; they create
    no graphics by design.
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

**W12 prepared under D28** (2026-11-01, plan
`2026-10-31-upstream-host-changes.md`):
- **Rebased and tested** on the projects' current branches (runs
  `upstream-napari-291` and `upstream-qtpy-292`). The new tests pass, and
  every suite keeps its failing set: napari's `_vispy` and `_qt` suites, and
  qtpy's whole suite under PyQt5, PyQt6, PySide6 and PySide2.
- **Measured effects** (run `upstream-effects-293`):
  - The napari change matters only for a vispy whose `gl+` does not use
    PyOpenGL. With this project's wheel, importing napari's canvas then loads
    no GL library on Windows; with upstream vispy nothing changes. Since the
    final review, napari takes `GLError` only from an already-imported
    PyOpenGL, so it never imports PyOpenGL itself, not even at layer removal.
  - The qtpy change stops importing Qt6's OpenGL modules but never changes
    whether the system GL library is loaded. On Windows those imports do not
    load it; on Linux `PyQt6.QtGui` loads it anyway.
  - Stock PyQt6 cannot import `QtGui` on Linux without libGL, so neither
    change helps there.
- **Submission.** napari's and Spyder's AI policies require the user to submit
  both PRs personally. The briefs and patches are local, in
  `docs/upstream-drafts/`.
- **W16.** The stock napari 0.10.0 lock is prepared locally, with PyQt6 6.12.0
  because napari 0.10.0 excludes Qt 6.11.0. Its GUI runs wait for the user's
  go-ahead.

## Order

1. R1's instrumentation runs alongside everything below.
2. W4's fixtures and all of W5 are done; D8, D10-D17 and D19 are decided. The
   smooth line ends, the minimum smooth coverage and the Qt canvas release are
   fixed in local test builds and ship with R2.
3. W6 is done on local test wheels. W7's observer, Linux rows and lavapipe
   smooth-line measurement are done on test wheels; its Linux non-line findings
   are open. W10 is done on the R2 test wheel.
4. W8: the report is done. D18's napari parity under native presentation is done
   (runs 249 and 255).
5. W15 and R2 (fresh release build), then W11 at the release and W12 on approval.
6. Backlog as capacity allows. B19 and B18, its queued case through P3, are on
   the R2 branch, and so is B20's fix.
7. Performance (user, 2026-10-30): P1 (textures), P2, P3, P4, P5 and P6 are
   on the R2 branch.

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
    napari-threedee fixture suites. By D19, lines pass when they are correctly
    positioned and look right: a line suite may move to a positioned-line
    criterion, fixed and tested before its re-run, as D8's cases did. Everything
    else stays exact.
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
  - Give each napari parity run a fresh `NAPARI_CONFIG`. napari restores the
    window geometry earlier runs saved in that environment, and the vector
    layers fixture's `shapes_selected` depends on it (run `b19-readback-257`).
  - Wrap diagnostic launches with `tools/pool_watch_external.py` (D20). Never use
    the in-process `tools/pool_watch.py`, which crashed Tk processes.
  - Run `uv` from the repository root, never inside a source snapshot. There,
    uv treats the snapshot's `pyproject.toml` as the project and creates a
    `.venv` (run `perf-profile-261`).
  - Pin on-screen benchmark runs to the performance cores (D23) with run
    `perf-profile-261`'s `pinned_launch.py`, and keep its record. Unpinned,
    Windows ran non-foreground benchmark windows on efficiency cores.
  - Admissions also need the 23-job CI and a promotion review.
- **Hygiene.**
  - Follow AGENTS.md: 20 GiB scratch and a 10 GiB reserve.
  - Use `UV_LINK_MODE=copy`.
  - Provision temporary interpreters with `--no-registry`.
  - Never repeat a benchmark run identically.
  - Write a run's terminal manifest only after everything that writes to its
    folder has stopped. Stop or finish its PR check watch first, and send the
    retain script's own output elsewhere.
  - Retain a main-tree source by its published commit, or copy an unpublished
    one into the run folder; never retain it by its working-tree path. 46 files
    retained that way in 19 earlier runs changed later (see Progress).
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
- **Host changes (D28).** Fix in vispy first, upstream second, and with a
  strict-only host patch last. Every file in `compat/host-patches/` is
  registered in `compat/host-changes.json`, and hot-swap locks name stock hosts
  only; `tests/contract/test_host_change_registry.py` checks both.

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
| `plans/2026-10-31-upstream-host-changes.md` | Active: D28's upstream-first host changes (W12) and the napari 0.10.0 baseline (W16). |
| `docs/opengl-removal-status.md` | Refreshed on 2026-10-29 (B16). |
