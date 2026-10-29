# Scientific fixture coverage — current evidence

This inventory maps the revised v1 requirements in [the design spec](../specs/2026-10-08-vispy-vulkan-design.md) to independent references and actual candidate evidence. The machine-readable [report](../../../build/reports/scientific-fixture-coverage-current.json) records source/reference/report hashes, case selections and matched test nodes. The original inventory was CPU-only; the Native58 supplement below records new GPU evidence without renderer changes or changes to criteria after candidate execution.

Native58 update, 2026-10-21: [saved mesh/layout review](../../../build/mesh-layout-saved-review-root-4/result.json) SHA24e58de10783b54da44fa01d137ad042340e1bae57adb67e59e8fec31ed1e95b recomputes twelve exact whole-frame pairs from thirteen admitted upstream cases on Windows CPython3.12.8/NumPy2.5.3, NVIDIA RTX4090 Vulkan hardware. The required axes/colorbar candidate remains a real smooth-line refusal. All eight shutdown counters are zero in every candidate worker, and both external environments are cleaned. This is a Root-only saved review, not independent-person or all-platform admission. The [bounded row supplement](../../../build/reports/scientific-fixture-coverage-native58-mesh-layout.json) adds only the scopes below; the older pass23 report remains historical.

Color-volume update, 2026-10-21: [the installed RGB/RGBA packet](../../color-volume-wheel-regressions.md) adds24 successful fresh originals and24 matching installed Native58 candidate cases. All221184 final and36864 before-frame pixels match exactly, including alpha. Independent inspection rechecks48 actual case workers, two parent suites, package/native origins, native work, eight shutdown zeros and removed environments/cache. The [portable original manifest](../../../tests/reference/color-volume-opengl/manifest.json) is c8af8d76e1ecdaac1e21303a47ba75a7cce83cb269085a230e89cf0f127c4337. This updates V08 only; it is a finite Windows CPython3.12.8/NumPy2.4.6/NVIDIA RTX4090 cell, not universal volume, platform or release qualification. The historical185/39 reference aggregate is not recomputed or enlarged by this row update.

Linux color-volume update, 2026-10-21: [the separate software packet](../../color-volume-linux-software-regressions.md) passes24 fresh Mesa OpenGL originals followed by24 installed Linux Native58 Vulkan CPU llvmpipe candidates. Independent saved inspection recomputes221184 exact final and36864 before-frame pixels and joins actual driver images, explicit submit layer, process/native origins, zero shutdown counters and removal of owned Xvfb/environment/cache. Its [original manifest](../../../tests/reference/color-volume-linux-opengl/manifest.json) is971d48cee245e2551e27261052d09a04d83988864ebbb6393c292f5175dfe925. This extends V08 to one WSL software cell; it adds no native Linux GPU, Metal, other ABI/binding, performance or full-release qualification. The Windows source/reference bytes and historical185/39 aggregate remain unchanged.

Large-image update, 2026-10-21: [the full 4096 packet](../../large-image-wheel-regressions.md) passes four fresh originals followed by four installed Native58 candidates, each across four stages. Independent saved-byte inspection recomputes 268,435,456 exact paired full-frame pixels, analytic source/pan checks, repeated/return identity, stable texture/framebuffer identities, actual owned-target draws, 20 resident-zero counters per later candidate stage, eight shutdown zeros, actual worker/parent waits and removed environments/cache. The [original manifest](../../../tests/reference/large-image-opengl/manifest.json) is ace47caea32759727170debd5a08db2c3255b29296873090290f12a12670c4d2, byte-identical to the successful original run. This updates I09 only for the Native58 cp312 artifact against official VisPy 0.17.0/PyQt6 OpenGL on Windows CPython 3.12.8, NumPy 2.4.6, NVIDIA RTX 4090, driver 610.88. Other ABIs, bindings, providers, GPUs, drivers and remaining release requirements are unqualified. Historical 185/39 totals remain unchanged.

Large-volume update, 2026-10-22: [the benchmark-data quality packet](../../large-volume-wheel-regressions.md) passes all 24 fresh originals before all 24 installed Native58 candidates. Each has initial/repeat/probe7/probe73 frames at the exact 1024² or 2048² physical viewport on 256³ or 512³ data. Independent inspection checks 251,658,240 whole-frame paired pixels (maximum error 1 under the fixed bound 2, including alpha), all 48 visible-change checks, actual transfer functions/controls/source bytes, stable IDs, original legacy cube geometry, candidate resident/full-update warm work, conserved non-growing memory, 48 actual workers/two parents, eight shutdown zeros and removed environments/uv cache. The [unchanged original manifest](../../../tests/reference/large-volume-opengl/manifest.json) is af7919c6f59dca7addee614a674942697b33d53df3446df0cea422ef980bf2ac. This moves V09 from missing to incomplete for one Native58 cp312/Windows CPython 3.12.8/NumPy 2.4.6/PyQt6/NVIDIA RTX 4090/610.88 cell. All 24 per-workload scientific-admission links now bind the unchanged independent controls rerun in NumPy 2.4.6; see [the admission packet](../../volume-scientific-admissions.md). Performance, other ABIs/bindings/providers/GPUs/drivers, native Linux, Metal and remaining release requirements are unqualified. Historical 185/39 totals remain unchanged.

## Evidence boundary

The sealed [reference inventory](../../../build/reports/reference-inventory-current-pass-10.json) has **185 admitted captured variants and 39 unresolved attempts**. These are not 185 distinct requirements. The historical native pass23/w7 core report is **247 passed, 8 explicit historical stencil-wrapper deselections, exit 0**. Its command explicitly ignores both required wide-line test files. The eight point identity references were authored afterward and have no candidate result. Glue, DIVE, registered plugin, alternate Qt binding/platform and performance qualification are separate gates.

Pass23 also has 22 actual GPU-query/memory hardware checks and one actual 12-frame CPU/GPU collector join. They prove owned query completion, multiple submissions, FBO/capture/loss and Vulkan allocation/free attribution. Their GPU intervals exclude upload work before the first measured render pass, query resolve/readback and compositor/scanout; they do not prove input-to-visible latency. The current Qt error tests have 4 passes and prevent a native validation exception from aborting through Qt callbacks. They do not catch native access violations or describe old w5 wheel behavior.

All five w5 Windows standard CPython ABI wheels have genuine clean headless clear/Text/SDF/assets/rollback proof. This does not qualify five Qt bindings or desktop hosts. The newer compatible SDK repairs the legacy PySide2 DIVE first native initialization: both scoped image/export children now render and exit 0, but both full-frame comparisons fail at 2,178 pixels with a maximum difference of 64, including upstream alpha 255 versus candidate 200/218/243 around Qt text/icons. Neither is admitted. Original host scatter/private-marker-API and ordinary teardown failures remain separate.

A **passed** row closes only its stated bounded case. **Incomplete** means partial/compile-only/reference-only or failed/missing candidate evidence. **Missing** means no independent required workflow fixture was identified. **Upstream admission gap** preserves a pinned unchanged upstream failure. No successful adjacent case substitutes for these gaps.

The historical base inventory counted 71 scoped rows: 23 passed, 29 incomplete, 16 missing and 3 upstream admission gaps. Later bounded row updates above do not recompute that historical aggregate. Each passed row has actual matching candidate test nodes. The report seals 26 reference manifests, 49 source files and the separate artifact/report witnesses.

## Requirement table

| ID | Spec requirement | State | Coverage limit or remaining gap |
| --- | --- | --- | --- |
| I01 | Scalar float32, clim auto/narrow, nonunit gamma and continuous colormap/LUT | passed | Bounded asymmetric small images; not every dtype/control combination. |
| I02 | Scalar uint16 and signed int16 host-converted images | passed | Does not cover int8 or scalar uint8. |
| I03 | Scalar uint8 and int8 after host fix_data_dtype | missing | RGBA uint8 does not establish scalar uint8; no int8 fixture. |
| I04 | RGB(M,N,3) and RGBA(M,N,4) channel handling | incomplete | RGBA is covered by nearest/export/blend frames; RGB3 is missing and dtype/channel combinations are limited. |
| I05 | Nearest and linear image interpolation | passed | Small fixed frame only. |
| I06 | GPU-scaled scalar NaN is transparent | passed | Pinned napari auto/GPU texture path only. |
| I07 | CPU-scaled scalar NaN maps to lowest clim | missing | No public ImageVisual texture_format=None comparison. |
| I08 | RGB NaN lowest-clim handling and alpha NaN zero | missing | Finite transparent export does not establish per-channel NaN rules. |
| I09 | 4096x4096 scalar/RGBA resident quality and pan | passed | Four full 4096 scalar/RGBA nearest/linear cases, each with baseline/repeat/camera-pan/return, pass for Native58 cp312 against official VisPy 0.17.0/PyQt6 OpenGL on Windows CPython 3.12.8, NumPy 2.4.6, NVIDIA RTX 4090, driver 610.88. All 268,435,456 paired pixels match exact RGBA; analytic checks, persistent targets and 20 resident-zero counters pass. Readback waits are deliberate. Fractional interpolation/zoom, performance/no-wait/long-run memory, native Linux, Metal, other ABI/binding/provider/GPU/driver and remaining release requirements are unqualified. |
| L01 | Background zero, sparse/high positive categorical IDs | passed | Positive int32 categories 7,65537,16777473 only. |
| L02 | Negative IDs and exact >2^24 input-to-texture remap witness | incomplete | High-ID color works, but no negative IDs or explicit persisted uploaded remap witness. |
| L03 | Offset tile updates preserve outside pixels and other content revisions | incomplete | Host edit/refresh has final outside-color evidence; no multiscale inactive-level revision proof. A low-level patch alone cannot establish host tiling. |
| L04 | Multiscale selection and slice-change invalidation | missing | No independent multiscale image/label levels or dims slice changes. |
| U01 | Middle-of-buffer set_subdata preserves surrounding attributes | missing | Current buffer snapshots use full set_data; new point patch starts at offset zero. |
| U02 | Pending texture partial/full revisions preserve old draws and rendered FBO contents | passed | Three prewarmed sampler/rendered-texture revision cases only. |
| U03 | One-flush early DATA,DRAW,SIZE,later DATA matches exact GLIR filtering | incomplete | Resize is before the first public draw, rather than the specified one-flush command sequence. |
| U04 | Second-flush buffer update after an old draw has been parsed | passed | Bounded full-buffer revision case. |
| U05 | Indexed/instanced point source IDs, divisors, constants and ordered revisions | incomplete | Eight upstream references are newer than pass23; no candidate run. Seven public Program.draw and one explicit nonzero-first queue contract. |
| M01 | Six symbol faces/edges in a fixed point marker scene | passed | Only disc,square,diamond,triangle_up,cross,star; spherical disabled, one size/AA/scaling. |
| M02 | All inventoried symbols, small/large size, edge width, AA and scaling | passed under D17 | 2026-10-29: `tools/fixture_markers_all_symbols.py` (all 15 symbols, sizes 8/24, edges 0/2, both methods, AA 0/1, scene scaling) passes under the user-approved documented difference D17 on `444402` and the R2 test wheel: aliased edge ties flip at most 0.1% of the frame, on edge pixels only. The native63 originals below stay retained. Earlier: No all-symbol/size/AA/scaling matrix. |
| M03 | Both marker methods render correctly | incomplete | Composer tests build pipelines for points/instanced but do not render both scientific marker methods. |
| M04 | Spherical lighting and fragment depth occlusion | incomplete | Spherical variants compile; no independent lighting/depth frame. |
| M05 | Camera-only no-upload, color-only updates and full position replacement | missing | No scientific marker mutation/camera image corpus. |
| M06 | One million fixed-seed canonical structured markers | passed under D17 | 2026-10-29: `tools/fixture_markers_million.py` (one million fixed-seed markers, both methods) passes under D17: at most 0.5% of pixels beyond 2 levels (fractional point sizes; equal-depth occlusion in dense overlap). Earlier: Small composer/gloo frames do not establish the 1M workload. |
| M07 | One-pixel endpoints, joins, clipping, varyings, depth and topology | passed | Bounded single-sample exact pinned-driver qualification, not portable coverage of all raster alternatives. |
| M08 | Wide/smooth lines and depth/flat-varying semantics | passed under D15/D16 on the R2 test wheel | 2026-10-29: smooth cases use the smooth-line rule without the frame cap (D15) and the reference tests pin the reviewed shared-fixture replacement (D16); 17 of 18 pass (the 18th is the retained original depth capture) and the defined-depth successor 3 of 3. On `444402` the smooth cases exceed the edge bound until R2's line-end fix. Earlier: Sixteen valid upstream cases; one original undefined-depth failure retained. Pass23 excludes both wide test files. |
| M09 | Agg line caps/joins, acute/degenerate joins and DPI-scaled width | passed | 2026-10-29: `tools/fixture_agg_lines.py` covers every cap code, miter/round/bevel joins at right and acute angles, degenerate joins and px_scale 2 and 3; exact on `444402` and the R2 test wheel. Earlier: Width7 at DPI96, one right-angle/default round join and two caps only. |
| M10 | Rectangle, ellipse and polygon topology | passed | Fixed bounded scene; not host arrows/vectors/tracks. |
| M11 | Arrows, vectors, tracks and selection outlines used by admitted hosts | passed (D10) on the R2 test wheel | 2026-10-29: `tools/fixture_napari_vector_layers.py`: vectors exact; tracks and shapes_selected pass under D10 (tracks needs R2's minimum smooth coverage). Earlier: No independent public workflow corpus for these requirements. |
| E01 | Unshaded planar mesh with a clipping plane | passed | shading=None; one planar fixture only. |
| E02 | Flat/smooth shading and SurfacePlot | bounded pass | Windows CP312; asymmetric two-face mesh and7x5 SurfacePlot; fixed light; whole frames exact. |
| E03 | Inventoried mesh filters and filter composition | incomplete | Texture+two visual clipping planes, derivative Wireframe composition and pre-draw detach pass exactly; complete filter inventory and pending-draw invalidation remain open. |
| E04 | 3D cameras, planes and scene depth/stencil/polygon offset | incomplete | Fixed perspective camera and coplanar scene polygon-offset ordering pass exactly; broader scene depth/stencil/camera matrix remains open. |
| E05 | Grid/ViewBox clipping and multiple viewports | bounded pass | Two adjacent clipped Grid ViewBoxes with oversized red/green rectangles, exact gap/outside pixels; one offscreen layout. |
| E06 | Axes and colorbars integrated with scientific layout | passed (D9, D11) | 2026-10-29: mesh axes_colorbar passes under D9 and napari's colorbar overlay under D11, both on the R2 test wheels. Earlier: Current installed Native58 candidate refuses the required upstream-passing axes/colorbar scene at generated smooth-line consumer policy. |
| V01 | Seven scalar ray modes | passed | 32-cubed float32 ellipsoid, one orthographic camera and fixed controls. |
| V02 | Advertised volume/plane constructor raycasting modes | passed | One plane MIP workflow; dynamic host plane controls separate. |
| V03 | Nearest/linear MIP, clip plane and mesh-front ISO depth | passed | Limited interpolation/control/occlusion cases. |
| V04 | Analytic thresholds, gradients, attenuation, step and opacity controls | passed (D14) | 2026-10-29: `tools/fixture_napari_layer_controls.py` changes the iso threshold, attenuated-MIP attenuation, translucent opacity and ray step after a first frame; exact except volume_iso under D14. Earlier: Known MIP/MINIP values; ISO nonblank/reference rather than analytic threshold crossing. Controls not varied. |
| V05 | Categorical ISO fast/smooth and translucent with background zero | passed | 32-cubed positive label set only. |
| V06 | Categorical plane, clip and edit workflows | passed | One fixed camera/plane; does not prove mesh-front depth or all categorical controls. |
| V07 | Registered public dynamic plane position/rotation/clipping | documented failure (D8) | 2026-10-29: the four render-plane-scheduled cases stay failing and documented (D8): napari-threedee's smooth 3D manipulator strokes differ by up to 104 levels on the R2 test wheel. Earlier: Four public Qt timer-delivered references, paired NumPy2.4.6; installed candidate graphics pending wide lines. |
| V08 | RGB/RGBA volume variants exposed by legal admitted APIs | bounded pass | Exact 24-case installed Native58 packets on Windows/RTX4090 and WSL Linux/Mesa llvmpipe software, CPython3.12.8. All seven methods in both forms plus opacity, plane/linear, updates and channel transitions. Float32 auto textures/one camera only; native Linux hardware and other cells remain unqualified. |
| V09 | 256-cubed and 512-cubed quality/performance data | incomplete | 2026-10-29: W8 timed three of these workloads, paced, with native presentation, against upstream OpenGL (`docs/performance-report.md`). The 256-cubed MIP and translucent resident volumes at 1024 keep about 60 frames per second; the harness refuses upstream's resident runs, which re-upload two 76-byte buffers per frame. The 512-cubed iso volume with a full upload every frame runs at 1.9 frames per second against 5.3. The other 21 workloads and the other cells stay untimed. Earlier: All 24 large benchmark quality/residency workloads pass on the bounded Windows cp312/NumPy 2.4.6/PyQt6/RTX 4090/610.88 cell: both sizes, 1024/2048 viewports, MIP/translucent/iso, resident/full updates. All 251,658,240 paired pixels meet fixed RGBA error <=2 (observed <=1), no exclusions. All 24 scientific-admission records bind exact independent controls in the same NumPy 2.4.6 candidate cell. Timed performance and other cells remain open. |
| T01 | Licensed font, real CPU SDF atlas and rendered text | passed | OpenSans Ag15 single line, left/baseline anchor and rotation zero. |
| T02 | Anchor, rotation and newline semantics | bounded pass | OpenSans CPU SDF; Ag/newline/15 at left/top0deg, center/center30deg, right/bottom-90deg; exact full frames, glyph records and atlases. |
| T03 | Required DPI1,1.25,1.5 text captures | bounded pass | Numeric DPI96/120/144 all match exactly and produce three distinct frames; this is not monitor-move or physical desktop scale admission. |
| T04 | Annotation, axis labels, colorbars and scale bars | passed on the R2 test wheel | 2026-10-29: napari scale bar and axes overlays pass the smooth-line criterion and the colorbar passes under D11 (`tools/fixture_napari_layer_families.py`); host annotation placement remains open. Earlier: Rotated standalone text is now covered; axis/colorbar scene remains refused by smooth lines, and scale bars/host annotation placement remain open. |
| B01 | Opaque/translucent/translucent_no_depth/additive/minimum host modes | passed | Two RGBA layers, first opaque, top opacity.75 only. |
| B02 | Legal multiplicative host blending | missing | Pinned napari Blending enum and GL factor map expose it; no upstream blocker. |
| B03 | First-layer behavior, opacity mutation and multichannel additive order | passed | 2026-10-29: `tools/fixture_napari_layer_controls.py`: an opacity change, a first-layer transition and a reordered additive stack match exactly on `444402` and the R2 test wheel. Earlier: Finite export and one two-layer additive case only. |
| Q01 | Parentable shown QWidget, show/minimize/resize and genuine device recovery | passed | Bounded PyQt6 Windows lifecycle; not all desktop transitions. |
| Q02 | Existing-layout reparent, actual WinIdChange and shared-resource lifetimes | incomplete | Headless shared canvases and parent setter pass; actual shown peer close/reparent resource retention missing. |
| Q03 | Zero/minimized no-submit and welcome/overlay screenshot inclusion | incomplete | 2026-10-29: napari's sized export (`viewer.screenshot(size=...)`) matches exactly (`tools/fixture_napari_layer_families.py`); zero/minimized no-submit and overlay inclusion remain open. Earlier: Minimize/show and child widget construction are tested, without exact no-submit or overlay pixels. |
| Q04 | Monitor moves/screen_changed and DPI1/1.25/1.5/2 mapping | incomplete | Injected ratio arithmetic only; no actual monitor transition. |
| Q05 | Close in flight, actual surface loss and multicanvas recovery | incomplete | Genuine device loss and late-event detach covered; effectiveWinId is monkeypatched, not actual surface loss. |
| Q06 | Canvas render/native color capture region,size,alpha,row order,owned arrays | passed | Bounded sample1 typed FBO and native color path; does not admit every host screenshot API. |
| Q07 | Single-sample D24 depth numeric/crop capture | passed | Actual D24 quantization, not MSAA. |
| Q08 | Unchanged upstream public stencil wrapper admission | upstream admission gap | Eight stock pinned wrapper/facade failures explicitly deselected; external raw-GL oracle cannot admit them. |
| Q09 | Canonical single-sample stencil numeric/crop semantics | passed | Oracle uses public draws plus external PyOpenGL GL_STENCIL_INDEX reads; candidate uses public mode=stencil. |
| Q10 | MSAA4 asymmetric color resolve | passed | One sample4 color frame, not MSAA depth/stencil. |
| Q11 | MSAA depth/stencil behavior and full format/feature matrix | missing | Typed color/depth/stencil corpus is single-sample; explicit unsupported MSAA depth is not parity. |
| Q12 | PyQt5/PyQt6/PySide6 and Windows/Linux-X11/Metal/software Vulkan | incomplete | Only Windows PyQt6 shown render broadly qualified; five ABI headless consumers do not qualify alternate bindings/platforms. |
| Q13 | Keyboard,wheel,touch,focus,mouse and timer coordinate forwarding | incomplete | Actual headless timer/draw and plugin mouse workflows cover a subset. |
| H01 | Public host screenshot, layer removal and no hidden finish | passed (D13) | 2026-10-29: a layer removal followed by napari's public screenshot matches exactly; glFinish counts are recorded, not compared (D13). Earlier: Host fixtures call scene.render/on_draw; ordinary napari screenshot/removal/no-finish contract not completely captured. |
| H02 | Four admitted Glue public workflows on installed candidate | passed | 2026-10-28: all five Glue workflows pass on `444402` (W13; scatter_axes under D5); the volume failure no longer occurs. Earlier: Installed w5 scatter/scatter_edit pass; scatter_axes rejects line_smooth and volume fails fixed pixels. Not pass23 host proof. |
| H03 | Glue volume mutation upstream admission | upstream admission gap | Pinned unchanged upstream volume_edit remains unresolved. |
| H04 | DIVE ordinary scatter/application teardown | upstream admission gap | Private _marker_funcs host/API incompatibility and original teardown failures remain; style restoration is scoped. |
| H05 | Scoped DIVE image/export style-restoration comparisons | incomplete | Compatible w8b repairs first-init; both children exit0/landmarks pass but full-frame comparisons fail2178pixels/max64 (Qt alpha255 vs200/218/243). |
| H06 | Genuine registered napari-threedee layer overlay picking/mutation/retirement | passed | 2026-10-28: the napari-threedee overlay passes 5 of 5 (smooth-line criterion, D5) on `444402` and the R2 test wheels. Earlier: Five independent references; installed w5 fails unsupported width3. CPU ray/sphere picking, not GPU ID picking. |
| H07 | Other admitted host workflows (visbrain, phylib and application-specific visuals) | incomplete | Source/import inventories do not qualify real rendered workflows; relevant unadmitted APIs remain explicit. |

The JSON report identifies the exact reference cases and pass23 test nodes for each bounded proof. Its source/artifact hashes distinguish current pass23, old installedw5, compatible DIVEw8b and upstream-only packets. Raw gloo state tests do not establish corresponding scientific scene or host behavior.

## Next three independent fixture packets

These packets follow the runtime point/inactive-resource, compatible SDK/legacy Qt and wide/smooth dependencies in the root plan. Independent upstream authoring can proceed before the candidate implementation. Freeze legal public API setup, data, analytic landmarks and criteria first; preserve all failed attempts and avoid candidate-fitted tolerances.

### 1. Image scaling, categorical revisions and legal blending

Asymmetric scalar uint8/int8 and RGB3 uploads; Separate CPU/GPU NaN and RGBA alpha-NaN semantics; Negative/high label IDs with persisted host-remap codes; Offset tile, selected multiscale level and slice changes with distinct content; Multiplicative and multichannel additive/first-layer order. Use vispy.visuals.ImageVisual(texture_format=None/r32f); napari.Viewer.add_image(rgb,multiscale,locked_data_level,blending); napari.Viewer.add_labels with DirectLabelColormap; layer.data/refresh and viewer.dims.set_point.

Proposed files: `tools/fixture_image_extensions.py`, `tools/oracle_image_extensions_capture.py`, `tests/hosts/test_image_extensions_parity.py`, `tests/reference/image-extensions-opengl`.

- Freeze input arrays, legal host remap, CPU analytic landmarks and tolerances before candidate.
- Independent installed upstream exit0, origin/version/source/artifact hashes and actual upload format/sample evidence.
- Outside tile and inactive-level pixels/content revisions unchanged; full refresh alone does not pass.
- Use public APIs, actual pending updates and one final dependent readback.
- Matched candidate environment passes unchanged full-frame criteria and ordered upload evidence.

Dependencies: Independent upstream authoring is ready; candidate requires matched qualified artifact/environment. Level and slice invalidation may expose separate runtime implementation gaps.

### 2. Rendered marker methods, spherical depth and revisions

Both methods with symbol/size/edge grid; Antialias and fixed/scene/visual scaling camera changes; Spherical light/ambient, overlapping markers and front mesh; Resident camera pan with no vertex upload; Color-only and full-position revisions before final read. Use vispy.visuals.MarkersVisual(method=points/instanced,spherical,antialias,scaling); MarkersVisual.set_data canonical pos/size/edge_width/edge_color/face_color/symbol; Public camera transform and scene Mesh.

Proposed files: `tools/fixture_marker_extensions.py`, `tools/oracle_marker_extensions_capture.py`, `tests/parity/test_marker_extensions_parity.py`, `tests/reference/marker-extensions-opengl`.

- Fixed canonical structured data and independent analytic light/depth/coverage landmarks before candidate.
- Actual draw/read pixels for both methods; compile_variant success is insufficient.
- Pending updates preserve old draws and outside data before one final readback.
- Camera changes pixels with zero vertex upload/compiler misses.
- Persist 1M seed/layout later for mandatory workload benchmark; small frame admission does not close 1M.

Dependencies: Matched native point identity/inactive-input/budget tests precede candidate instanced qualification. Independent upstream capture does not require candidate implementation.

### 3. Shaded mesh, filters, clipped layout and annotations

Asymmetric flat/smooth meshes and SurfacePlot with known normals; Textured/wireframe/clipped filter composition; Perspective camera and scene depth/offset ordering; Adjacent clipped Grid ViewBoxes and linked axes/colorbar; Rotated multiline anchors at DPI96/120/144. Use vispy.scene.visuals.Mesh(shading=flat/smooth) and SurfacePlot; Visual.attach/detach with Texture/Wireframe/PlanesClipper filters; Grid.add_view, AxisWidget.link_view, ColorBarWidget; TextVisual rotation/anchors/newline and actual FontManager/SDF atlas.

Proposed files: `tools/fixture_mesh_layout_extensions.py`, `tools/oracle_mesh_layout_extensions_capture.py`, `tests/parity/test_mesh_layout_extensions_parity.py`, `tests/reference/mesh-layout-extensions-opengl`.

- Freeze normals, colors, clipping intersections, view boundaries and text geometry before candidate.
- Independent actual upstream render+shader/format evidence and licensed CPU atlas hashes.
- Exact text atlas/frame; fixed independently declared geometry edge bands only.
- No ViewBox spill and correct camera/annotation physical landmarks.
- Actual candidate pixels/filter pipelines and cleanup; axis/wireframe wide-line dependencies remain explicit.

Dependencies: Wide/smooth implementation before candidate axis/wireframe qualification. Image LUT packet supplies host colormap control evidence; standalone layout remains independent.

## Required scope after these packets

- Scalar/categorical volume controls, analytic isovalue/gradient/depth, RGB(A) volumes and large256/512cubed quality.
- Shown Qt sharing/reparent/surface/monitor-DPI/overlay/input matrix for PyQt5/PyQt6/PySide6.
- MSAA depth/stencil and admitted format/feature/shader-binding matrix.
- Linux X11, Metal, software Vulkan and platform-specific hosts.
- Visible latency and Metal GPU timestamp telemetry.
- Final matched all-ABI installed consumers/host suite followed by fixed-quality100warm/1000sample/5alternating-trial performance gates.

## Completion plan audit

- Root's eight-phase dependency order is sound; keep full original13-step scope.
- Wide-line and indexed-point repairs do not establish scientific marker spherical shading/depth or camera/revision behavior.
- Add required120DPI (1.25), multiline/rotation, legal multiplicative mode, CPU-vs-GPU NaNs, multiscale/slice invalidation, exact one-flush DATA/DRAW/SIZE/DATA and middle-buffer patch as distinct gates.
- All5ABI headless clean consumers are packaging evidence, not alternative Qt binding/platform render proof.
- Compatible SDK/CRT init repair does not close DIVE screenshot alpha parity or ordinary scatter/application teardown.
- Public plugin picking is CPU ray/sphere; no GPU ID-pick qualification claim.
- Do not substitute filtered-upstream failures, compiler-only pipelines, small data or old installed wheel for matched native scientific render/performance evidence.

