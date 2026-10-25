# API implementation routes and acceptance map

Date: 2026-10-25. This is an execution aid for the active compatibility plan.
“API key” means the stable feature identifier used by the inventory. These
routes are proposed engineering choices, not support or qualification claims.
They cover every current canonical feature key plus all 15 additive candidate
keys. The inventory remains the authority for requirements and applicability;
this document creates no new completeness denominator and discharges no parent.

## How to choose the easiest faithful route

First reuse the existing Python API and native GLIR mechanism, then fix the
smallest reproduced mismatch. Preserve public signatures, values, errors,
mutation, ownership and visible output. A wrapper over a shared working primitive
usually needs an integration vector rather than a separate renderer. Distinct
observables still need distinct assertions. Each whole execution row retains
ordinary/mutation/failure/recovery proof and its same-profile dependencies.

Use one scenario result for several criteria only when its reviewed mapping
proves every criterion and required branch. Do not perform 120 separate launches
for 120 bindings, but do not use one generic screenshot to cover all 142 parents.
Full-parent coverage needs method/value/event/example reconciliation beyond a
class import or constructor. Source success still needs exact installed-origin,
functional/absence/control/shutdown and artifact review before admission.

## Current candidate: 15 API keys

Source implementations and composite scripts already exist. The fastest next
step is review, applicable-blocker resolution and installed qualification, not
rewriting these APIs. Use the three existing scenarios in `tools/tkinter_*_scenario.py`
and their current coverage mappings. The failure composite retains all eight
required branches. Each row below keeps its explicit exclusions in candidate.json.

| API key | Public entry points | Lowest-change route | Decisive acceptance | Prerequisite |
| --- | --- | --- | --- | --- |
| `tk.backend.raster` | `vispy.app.Application(tkinter)` | Keep the existing Tk raster presenter; fix only a reproduced lifecycle/capability mismatch. | Existing Tk state composite; independently expected corners, resize and borrowed-root survival. | Backend/profile admission |
| `tk.application.manual` | `Application.process_events`, `Application.quit` | Reuse Application.process_events/quit and the current error channel; share the loop core with owned/borrowed drivers. | Pump, deliver the first exception once, stop public timers and preserve unrelated root work. | `tk.backend.raster` |
| `tk.canvas.basic` | `Canvas`, `Canvas.update`, `Canvas.close`, `Canvas.set_current` | Reuse Canvas and the raster backend; add finite configuration/coordinate cases rather than another Canvas implementation. | Update/resize/close twice and context switching; independent output and no remaining owned callbacks. | `tk.application.manual` |
| `tk.context.current` | `GLContext.flush_commands`, `Canvas.context` | Use the existing context/GLIR/native submission bridge; keep context identity explicit. | Switch two canvases, flush the intended queue and verify no submission on the other canvas. | `tk.canvas.basic` |
| `tk.context.shared` | `Canvas(shared=first)`, `GLContext.shared` | Reuse GLContext.shared and existing resource ownership; test new sharing orders as additional vectors. | Two canvases share a resource; close its creator, draw on survivor, then delete without leaked owners. | `tk.context.current` |
| `tk.canvas.recovery` | `Canvas.update after device recreation` | Keep explicit device recreation and resource reconstruction; do not invent automatic success retries. | Injected loss, explicit recreation, exact survivor image and shutdown baseline. | `tk.canvas.basic`, `tk.context.current` |
| `tk.timer.once` | `Timer.start`, `Timer.stop`, `Timer.events.timeout` | Reuse Timer public state and backend scheduling; extend one timer test table for restart/interval/loop modes. | Exactly one timeout, stop on failure/quit, no callback after close; restart separately. | `tk.application.manual` |
| `tk.gl.flush` | `gl.glFlush` | Retain the shared raw/gloo native submit route; finish installed evidence before touching the implementation again. | All four route/delay capacity variants; no implicit wait/present, retirement then one explicit retry. | `tk.context.current` |
| `tk.wrappers.submission` | `gloo.clear`, `gloo.flush`, `gloo.finish` | Use the same submission bridge; compare wrapper semantics with raw calls in one composite. | clear/flush/finish ordering and counters before readback can conceal a no-op. | `tk.gl.flush`, `tk.context.current` |
| `tk.wrappers.raster` | `gloo.set_viewport`, `gloo.set_state`, `gloo.finish` | Keep wrappers as state authoring over the existing native state cache; use finite enum/value vectors. | Viewport/scissor/masks/blend mutations affect only the expected pixels and invalid input preserves queue/state. | `tk.context.current` |
| `tk.readback.rgba` | `gloo.read_pixels` | Reuse existing readback conversion; extend capture vectors for crop/type/odd dimensions after the selected RGBA case. | Independent asymmetric RGBA expectation; avoid comparison of two paths sharing the same orientation bug. | `tk.context.current` |
| `tk.object.delete` | `GLObject.delete` | Reuse shared owner/ticket retirement; parameterize object type and delete order. | Delete before/after submit, duplicate delete, survivor draw and baseline resource counts. | `tk.context.current` |
| `tk.buffer.triangle` | `VertexBuffer` | Keep VertexBuffer and typed upload path; add index/stride/divisor cases through the common buffer mechanism. | Triangle changes after upload, shares across canvases and retires safely after owner deletion. | `tk.context.shared`, `tk.object.delete` |
| `tk.texture.rgba8` | `Texture2D`, `Texture2D.set_data` | Reuse Texture2D upload/cache/recovery; test subuploads/formats in a shared texture suite. | Exact colored texels before/after mutation, actual upload failure/recovery and retained queued revision. | `tk.context.shared`, `tk.object.delete`, `tk.canvas.recovery` |
| `tk.program.texture` | `Program`, `Program.draw` | Reuse Program compilation/reflection and the existing textured draw; keep new shader interfaces in SH packets. | Bound program/buffer/texture mutation, shared survivor, loss/recreate and exact pixels. | `tk.context.shared`, `tk.buffer.triangle`, `tk.texture.rgba8`, `tk.object.delete` |

## Canonical API keys: first implementation route

These are discovery/repair routes for each original parent, not assertions that
the full parent already works. Run the distinguishing vector before editing.
If it passes, preserve the implementation and fill missing method/value/profile
evidence instead. A failed vector selects the shared mechanism to repair.

### Application and backend API keys

| API key | Preferred implementation route | First decisive vector / remaining scope |
| --- | --- | --- |
| `app.application` | Retain Application as the common adapter; repair shared loop/root ownership once. | Owned run, manual pump and borrowed loop each deliver errors once and quit without destroying another app. |
| `app.backend.egl` | Inventory actual EGL consumer semantics first; reuse Dawn headless offscreen for GL-free rendering only where the API contract permits it. | Offscreen behavior and context/current/config expectations; headless substitution cannot claim native EGL/GL handle interoperability. |
| `app.backend.glfw` | Check the pinned GLFW no-client-API window path; reuse common raster/readback only if a real toolkit image presenter exists, otherwise design WSI under strict observer checks. | Real displayed resize/input/capture and failure/close; no GL context creation or hidden headless stand-in. |
| `app.backend.jupyter-rfb` | Reuse existing jupyter_rfb image transport and backend adapter; feed Dawn readback instead of a GL context. | Actual notebook frontend frame/update/input/disconnect round trip, server cleanup and separately pinned browser/server scope. |
| `app.backend.osmesa` | Separate requested offscreen pixels from explicit OSMesa ABI consumers; reuse headless only for the former. | Independent software output and buffer/readback lifecycle; arbitrary OSMesa/GL handles remain unresolved without a faithful no-GL design. |
| `app.backend.pyglet` | First verify that the pinned toolkit can create a window and present images without initializing GL; then adapt the common presenter. | Actual window/import/transient/API observation; if toolkit forces GL, retain blocker and compare a compatible version before any rewrite. |
| `app.backend.pyqt4` | Assess an available pinned interpreter/Qt4 binding first; reuse shared Qt raster adapter only if its APIs work. | Real Qt4 event/input/presentation and closure under its own profile; newer Qt cannot stand in for unavailable Qt4. |
| `app.backend.pyqt5` | Reuse the existing Qt raster implementation and exact PyQt5 consumer. | Existing installed Qt/host matrix plus changed dependency reruns; no QOpenGLWidget/native WSI shortcut. |
| `app.backend.pyqt6` | Reuse the same Qt raster implementation with PyQt6 enum/event adaptations. | Actual PyQt6 host lifecycle/input/resize/capture/recovery and original absence gates. |
| `app.backend.pyside` | Check pinned legacy PySide/interpreter availability before adapter edits; reuse shared Qt raster code where compatible. | Real binding/version profile and ownership tests; unavailable runtime remains a blocker, not nonapplicability. |
| `app.backend.pyside2` | Use the already pinned legacy-compatible Python environment if available; adapt common Qt raster ownership/signals. | Real PySide2 render/input/capture/quit and source/member closure; PySide6 receipts cannot transfer. |
| `app.backend.pyside6` | Reuse existing PySide6 Qt raster adapter; focus on lifetime/ownership differences. | Real PySide6 public and host workflows plus signal/object teardown and absence gates. |
| `app.backend.sdl2` | Prefer SDL window plus a positively identified software image presenter; exclude SDL GL renderer selection. | Displayed frames, resize/DPI, input and renderer backend identity; observe actual transient/dependency/API behavior. |
| `app.backend.tkinter` | Finish current Tk candidate qualification using existing raster/photo image route; expand remaining Canvas/loop/input vectors afterward. | All three loop drivers, NoDefaultRoot/embedding, device loss, capture and true camera drags; selected narrow proof does not cover whole parent. |
| `app.backend.wx` | Assess wx.Panel/bitmap paint route and reuse common pixel presentation/lifecycle rather than wx.GLCanvas. | Real wx paint/event/DPI/capture/recovery and borrowed-parent close with absence gates. |
| `app.base` | Keep backend base interfaces; derive a single capability/ownership contract reused by backend adapters. | Contract conformance plus one real adapter workflow; abstract/import-only tests cannot admit a backend. |
| `app.canvas` | Reuse Canvas/context and presenter separation; parameterize constructor and capture options. | Lifecycle/resize/px_scale/capture/input, invalid construction unwind and shared-context survivor. |
| `app.create` | Route factory selection through existing backend registry and Canvas. | Selected backend/profile actually draws; invalid selection fails before native allocations. |
| `app.keyevent` | Reuse KeyEvent/EventEmitter translation; add toolkit mapping vectors rather than new event types. | Modifiers, press/release, repeat and focus changes match public values and consumer callbacks. |
| `app.mouseevent` | Reuse MouseEvent and maintained button state across adapters. | Multi-button drag, wheel, outside release and focus loss move real PanZoom/3D cameras correctly. |
| `app.process-events` | Delegate to the common app pump; repair first-error delivery in one place. | Progress, draw and timer ordering; first traceback once, bounded return and unrelated root callbacks survive. |
| `app.quit` | Stop public Timer objects and owned loops/resources through existing ownership code. | Timer.running false, no callbacks after quit, external root and another Application remain usable. |
| `app.run` | Use the same error/progress core as manual pumping; keep owned versus borrowed loop exit explicit. | Real owned mainloop exits on intended failure with original traceback; borrowed loop reports without destroying host. |
| `app.timer` | Extend existing Timer and backend scheduling table across intervals, iterations and restart. | Start/stop/restart/change interval in each loop driver; no post-close timeout and correct public state. |
| `app.use-app` | Reuse registry and existing Application singleton rules. | Selection/reselection errors and already-imported toolkit preferences; verify actual chosen backend. |

### Low-level gloo API keys

| API key | Preferred implementation route | First decisive vector / remaining scope |
| --- | --- | --- |
| `gloo.framebuffer` | Keep existing attachment/FBO model and Dawn targets; add format/sample/depth/stencil combinations as vectors. | Attach/replace/delete, resize, completeness failures and independent color/depth/stencil outputs on actual sample counts. |
| `gloo.get-current-canvas` | Reuse existing current-canvas tracking shared by Canvas and context dispatch. | Two canvases, nested set_current/close, no canvas and thread rules; command reaches intended target. |
| `gloo.get-default-config` | Reuse public config normalization with explicit Dawn capability limits. | Defaults remain deterministic; returned mutable dictionaries do not corrupt later defaults; unsupported values diagnose clearly. |
| `gloo.get-gl-configuration` | Return logical/granted configuration through the existing query path. | Requested versus actually granted samples/depth/stencil/doublebuffer; no fabricated GL context attributes. |
| `gloo.gl` | Inventory raw proxy operations beyond state/query: map object creation/bind/upload/shader/draw selectors onto existing native GLIR owners. | Handle identity, return/error/query behavior and actual output across raw and gloo routes; allowlisting state alone cannot close this parent. |
| `gloo.glcontext` | Reuse GLIR context/share/current/flush machinery and make ownership transitions explicit. | Cross-canvas current selection, shared resources, flush/finish, loss and close; no real GL context required by selected path. |
| `gloo.globject` | Reuse native owner IDs and retirement tickets across object subclasses. | Delete queued/in-flight/shared objects, repeated delete and explicit loss; no use-after-retirement or leaked owners. |
| `gloo.indexbuffer` | Reuse typed buffer upload and index topology path; parameterize uint sizes and partial updates. | Indexed primitive output, offset/range validation, queued updates and instanced draws where public API supports them. |
| `gloo.program` | Reuse existing compiler/reflection/bindings/Program; address SH-1..5 through shared lowerings only when consumer requires them. | Shader diagnostics, uniforms/samplers/attributes, draw modes, mutations, resource limits and independent pixels. |
| `gloo.read-pixels` | Extend current readback/conversion rather than adding another capture stack. | Odd dimensions/origin/crop/type/alpha/depth and actual MSAA target; expected data independent of candidate readback. |
| `gloo.renderbuffer` | Reuse target storage descriptor/allocation; enumerate supported formats and sample counts. | Allocation/resize/attachment errors, actual granted storage, depth/stencil interactions and retirement. |
| `gloo.texture1d` | Lower 1D storage through existing texture descriptors with dimension-specific sampling coordinates. | Length/filter/wrap/mipmap, subupdate and independent texel expectation; cannot simply relabel a 2D API. |
| `gloo.texture2d` | Reuse current texture upload/sampling/cache path and expand shape/format/subupdate table. | Integer/float/normalized formats, alignment/filter/wrap, queued revisions and recovery. |
| `gloo.texture3d` | Reuse native 3D texture/volume mechanisms; test dimensions and z subregions. | Independent slice/volume sampling, strides/format/limits, partial upload and device recovery. |
| `gloo.textureatlas` | Keep Python atlas packing over admitted Texture2D. | Allocation/packing/subimage/growth coordinates and sampled border texels; share Texture2D lifecycle proof. |
| `gloo.texturecube` | Reuse cube-view descriptors over six pinned face uploads. | Face ordering/orientation, mip/filter/seams, per-face updates and invalid shape errors. |
| `gloo.textureemulated3d` | Preserve atlas-based emulation as a Python/shader adapter over Texture2D. | Compare independent 3D sample positions/slice boundaries and mutations; do not replace its public contract with Texture3D silently. |
| `gloo.util` | Enumerate exported utilities first; reuse admitted program/buffer/framebuffer/readback primitives. | One contract per discovered helper behavior, including errors; module import is only discovery. |
| `gloo.vertexbuffer` | Reuse typed uploads/attribute layout; share SH-3 location expansion for matrix/array inputs. | Structured/interleaved/strided inputs, partial updates, instancing/divisors, limits and lifetime. |

### Scene, camera and widget API keys

| API key | Preferred implementation route | First decisive vector / remaining scope |
| --- | --- | --- |
| `scene.cameras` | Enumerate camera exports and reuse their Python transform/event logic. | Each concrete camera links to its own interaction/output vector; namespace import does not close aliases. |
| `scene.cameras.arcballcamera` | Keep the existing Python camera; repair event translation or transform binding once in shared layers. | Quaternion trackball drag/rotation around a known 3D object; verify projection and center. |
| `scene.cameras.basecamera` | Keep the existing Python camera; repair event translation or transform binding once in shared layers. | Shared view linkage, range/transform/reset/events and reuse across two views. |
| `scene.cameras.flycamera` | Keep the existing Python camera; repair event translation or transform binding once in shared layers. | Key and drag movement, repeat/focus loss, timer stop and known view matrix/output. |
| `scene.cameras.magnify1dcamera` | Keep the existing Python camera; repair event translation or transform binding once in shared layers. | One-axis magnification and cursor mapping; unaffected orthogonal axis stays unchanged. |
| `scene.cameras.magnifycamera` | Keep the existing Python camera; repair event translation or transform binding once in shared layers. | Lens position/radius/magnification mutation; independent transformed sample positions. |
| `scene.cameras.make-camera` | Keep the existing Python camera; repair event translation or transform binding once in shared layers. | Each supported factory selector and parameters produces the correct concrete type/behavior; invalid selector fails. |
| `scene.cameras.panzoomcamera` | Keep the existing Python camera; repair event translation or transform binding once in shared layers. | Pan/zoom/aspect/range/invert with actual drag/wheel; check coordinates and visible image. |
| `scene.cameras.turntablecamera` | Keep the existing Python camera; repair event translation or transform binding once in shared layers. | Azimuth/elevation/distance/fov/center and actual drag; independent matrix/output. |
| `scene.filters` | Resolve namespace aliases to concrete visual filter implementations; share their shader-hook tests. | All exports retain identity plus actual attached filter behavior; no duplicate renderer port for an alias. |
| `scene.node` | Keep Python scene graph and transform propagation; test it over an admitted SceneCanvas. | Parent/reparent/order/visibility/clipping changes and event propagation affect intended draws. |
| `scene.scenecanvas` | Reuse current Canvas plus scene traversal and target-stack machinery. | Multiple views, transforms/clips, render/capture, camera input, resize and cleanup. |
| `scene.transforms` | Map aliases to existing transform types and shader composition; reuse the transform suite. | CPU map/imap and rendered shader transform agree against independent points; all aliases reconciled. |
| `scene.visuals` | Map scene visual wrappers to concrete visual families and Node integration. | Wrapper creation/parenting/events plus underlying rendering; wildcard exports require explicit enumeration. |
| `scene.widgets` | Enumerate widgets and retain Python layout over admitted scene/mesh/line/text. | Nested layouts with distinct size constraints, resize and visible output per concrete widget. |
| `scene.widgets.axiswidget` | Reuse Python layout/composition and admitted scene primitives; port only a concrete backend-dependent call. | Tick/label alignment and linked view-range changes; reuse AxisVisual and TextVisual. |
| `scene.widgets.colorbarwidget` | Reuse Python layout/composition and admitted scene primitives; port only a concrete backend-dependent call. | Color/limits/orientation/label layout updates; reuse ColorBarVisual. |
| `scene.widgets.console` | Reuse Python layout/composition and admitted scene primitives; port only a concrete backend-dependent call. | Actual input/output/editing/event behavior and focus/lifetime; inventory toolkit assumptions first. |
| `scene.widgets.grid` | Reuse Python layout/composition and admitted scene primitives; port only a concrete backend-dependent call. | Cell spans/spacing/margins/nested sizing and resize; assert independent rectangles. |
| `scene.widgets.label` | Reuse Python layout/composition and admitted scene primitives; port only a concrete backend-dependent call. | Text/font/color/alignment resize and clipping; reuse TextVisual/SDF. |
| `scene.widgets.viewbox` | Reuse Python layout/composition and admitted scene primitives; port only a concrete backend-dependent call. | Multiple scenes/cameras, clipping/framebuffer stack and camera interaction after resize. |
| `scene.widgets.widget` | Reuse Python layout/composition and admitted scene primitives; port only a concrete backend-dependent call. | Geometry/margin/padding/border/background/visibility; compose existing mesh/scene primitives. |

### Visual, filter, shader-authoring and transform API keys

CPU geometry/layout/math should stay in Python. Reuse admitted mesh/line/point/
texture/program operations for their GPU work. A passing base mechanism saves
implementation duplication; it does not prove every subclass or filter value.

| API key | Preferred implementation route | First decisive vector / remaining scope |
| --- | --- | --- |
| `visuals.arrowvisual` | Reuse LineVisual plus mesh/instanced arrowheads; isolate any geometry dependency. | Arrow position/size/orientation, clipped/degenerate segments and mutation; SH-4 only if an actual consumer requires it. |
| `visuals.axisvisual` | Compose existing line/tick/text primitives; keep CPU tick layout. | Range/orientation/tick labels and resize against independent expected positions. |
| `visuals.basevisual` | Preserve Visual state/update/draw lifecycle; fix common shader/context hooks once. | Draw/update events, visibility, shared state and cleanup with a minimal concrete subclass. |
| `visuals.boxvisual` | Keep CPU box geometry over MeshVisual/LineVisual. | Face/edge colors, dimensions/transforms and updates; independent geometry and visible faces. |
| `visuals.colorbarvisual` | Reuse texture/mesh gradient plus line/text labels. | Limits, colormap, orientation, label mutations and independently expected colors. |
| `visuals.compleximagevisual` | Preserve complex-to-scalar/color mapping over admitted ImageVisual. | Known complex values, magnitude/phase/real/imag modes and clim/colormap updates. |
| `visuals.compoundvisual` | Keep Python child visual composition and shared transforms. | Child ordering/visibility/add-remove, update propagation and no double resource release. |
| `visuals.cubevisual` | Reuse shared box/mesh geometry; preserve public constructor semantics. | Six-face colors, edge width and orientation/size mutations; no separate primitive renderer. |
| `visuals.ellipsevisual` | Use existing CPU tessellation and Mesh/Line primitives. | Center/radii/arc/segments, fill/border mutations, degenerate and transformed output. |
| `visuals.filters.alpha` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | One attached alpha multiplier; blend with distinct background, mutate alpha and preserve depth policy. |
| `visuals.filters.clipper` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | Transform clip coordinates and fragment discard through existing shader hooks; outside/edge/inside points plus transformed clip updates. |
| `visuals.filters.colorfilter` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | Existing color function/hook; unequal channel transforms and mutation must affect only intended visual. |
| `visuals.filters.facepickingfilter` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | Reuse deterministic primitive/face ID encoding on a picking target; exact IDs, occlusion, resize and updates. |
| `visuals.filters.filter` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | Retain attach/detach/hooks and shader dependency invalidation; order two filters and mutate/remove one. |
| `visuals.filters.instancedshadingfilter` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | Reuse instanced normal/lighting data; different instance transforms and normals, then SH-3 only for unsupported attributes. |
| `visuals.filters.isolinefilter` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | Preserve scalar interpolation/derivatives in fragment hooks; known levels, width and transformed mesh output. |
| `visuals.filters.markerpickingfilter` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | Reuse marker instance IDs and picking target; exact IDs after data reorder, overlap and clipping. |
| `visuals.filters.pickingfilter` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | Share picking encoding/framebuffer/readback; verify IDs against authored objects and background sentinel. |
| `visuals.filters.primitivepickingfilter` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | Identify indexed/nonindexed primitive numbering and provocation; exact triangle/line IDs after mutation. |
| `visuals.filters.shadingfilter` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | Keep existing lighting shader composition; independently expected normals/material/light changes and flat/smooth behavior. |
| `visuals.filters.texturefilter` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | Reuse texture/sampler binding and mesh UVs; asymmetric texture orientation, wrapping and rebinding. |
| `visuals.filters.wireframefilter` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | Prefer the current barycentric/mesh representation when semantics permit; if geometry stage is required, first inventory exact topology then SH-4. |
| `visuals.filters.zcolormapfilter` | Reuse existing filter shader hooks on the admitted mesh/marker/program mechanism; preserve API attachment/order. | Reuse z-coordinate varying and colormap texture; known heights/clim with transformed geometry and updates. |
| `visuals.graphvisual` | Compose admitted lines/arrows/markers and Python graph layout. | Directed/undirected edges, node/edge style updates, layout change and empty graph. |
| `visuals.gridlinesvisual` | Reuse fragment transform/uniform logic on existing quad/line mechanisms. | Pan/zoom/log transforms, spacing/alpha and clipping; independently predicted grid intersections. |
| `visuals.gridmeshvisual` | Keep CPU grid topology and shared mesh/shading path. | Non-square grid, scalar/color updates, normals and invalid shape errors. |
| `visuals.histogramvisual` | Keep CPU binning/geometry over mesh. | Known bins/counts, orientation/range/color changes and empty/constant input. |
| `visuals.imagevisual` | Reuse installed image suite and texture/quad path; target missing method/format cases. | Scalar/RGBA, clim/interpolation/colormap/subupdate and orientation/capture; preserve independent references. |
| `visuals.infinitelinevisual` | Reuse transform-aware line primitive with CPU endpoints or existing shader. | Horizontal/vertical position, zoom/clip, width/color and nondefault viewport. |
| `visuals.instancedmeshvisual` | Reuse MeshVisual with existing instance data path; resolve SH-3 for actual matrix/array attributes. | Distinct per-instance transforms/colors/divisors and mutations near real vertex-input limits. |
| `visuals.isocurvevisual` | Keep CPU contour extraction over LineVisual. | Known scalar field/level curves, disconnected/degenerate paths and data/level mutations. |
| `visuals.isolinevisual` | Identify whether consumer uses mesh fragment isolines or line extraction; reuse that path. | Known isoline levels/width/interpolation, clipping and shader-hook updates; keep SH-4 boundaries explicit. |
| `visuals.isosurfacevisual` | Keep CPU marching-cubes output over MeshVisual. | Analytic sphere field surface/normals, level/data changes and empty/degenerate volume. |
| `visuals.linearregionvisual` | Reuse a small mesh/line composite and transform layer. | Horizontal/vertical bounds, colors, clipping and updates without rebuilding unrelated geometry. |
| `visuals.lineplotvisual` | Compose LineVisual and MarkersVisual; keep shared Python data normalization. | Line/marker style combinations, finite/nonfinite data policy, data updates and cleanup. |
| `visuals.linevisual` | Reuse ordinary/generated line lowerings and existing corpus; do not remove side-effect guards. | Strip/segments/joins/caps/width, clipping/degenerates, indexed/instanced mutation; SH-5 for guarded evaluators. |
| `visuals.markersvisual` | Reuse existing point/marker compiler and installed smoke/corpus. | Symbol/size/edge/scaling/antialias states, per-marker updates and clipping/resource limits. |
| `visuals.meshnormalsvisual` | Generate normals/line endpoints on CPU where the existing API permits; render through LineVisual. | Face/vertex normals, length/color/data updates and transformed expected segments. |
| `visuals.meshvisual` | Reuse established mesh buffers/indices/shading/filter path and mesh-layout suite. | Structured layouts, colors/normals/indices, update/loss and independent rendered fixtures. |
| `visuals.planevisual` | Reuse CPU plane mesh plus admitted mesh/line. | Direction/size/segments, fill/edge style and transformed expected geometry. |
| `visuals.polygonvisual` | Keep existing CPU triangulation and border lines. | Concave polygon, winding/border/color mutations and invalid/degenerate input contract. |
| `visuals.rectanglevisual` | Reuse polygon/rounded-rectangle tessellation and shared primitives. | Bounds/radius/border updates and corners under clipping/transforms. |
| `visuals.regularpolygonvisual` | Reuse CPU polygon generation; share polygon/line renderer. | Sides/radius/rotation, fill/border mutations and minimum-side validation. |
| `visuals.scrollinglinesvisual` | Reuse existing ring-buffer/upload strategy over line rendering. | Wraparound, per-line offset, append/replace and mutation without stale queued revisions. |
| `visuals.shaders.compiler` | Keep Python shader authoring and existing native compiler/reflection; expand SH packets only for a named missing interface. | Preserve shader graph name/dependency resolution and compile to existing native pipeline; compare generated/reflected resources and diagnostics. |
| `visuals.shaders.function` | Keep Python shader authoring and existing native compiler/reflection; expand SH packets only for a named missing interface. | Keep Python GLSL function composition; arguments/dependencies/renaming/mutation and actual compiled pixel use. |
| `visuals.shaders.functionchain` | Keep Python shader authoring and existing native compiler/reflection; expand SH packets only for a named missing interface. | Reuse function composition ordering; noncommuting functions distinguish order and invalidate caches after chain edits. |
| `visuals.shaders.mainfunction` | Keep Python shader authoring and existing native compiler/reflection; expand SH packets only for a named missing interface. | Keep stage source/hook substitution; hook additions/removals and actual execution output, not string-only acceptance. |
| `visuals.shaders.modularprogram` | Keep Python shader authoring and existing native compiler/reflection; expand SH packets only for a named missing interface. | Reuse Program with shader graph dependency invalidation; uniforms/varyings/filters mutate without stale resources. |
| `visuals.shaders.multiprogram` | Keep Python shader authoring and existing native compiler/reflection; expand SH packets only for a named missing interface. | Reuse per-view/context Program instances with shared declarations; diverging views and resource changes remain isolated. |
| `visuals.shaders.statementlist` | Keep Python shader authoring and existing native compiler/reflection; expand SH packets only for a named missing interface. | Keep ordered GLSL statement assembly; insertion/removal and side-effect order verified by output/native compilation. |
| `visuals.shaders.variable` | Keep Python shader authoring and existing native compiler/reflection; expand SH packets only for a named missing interface. | Preserve type/value/interface inference and uploads; scalar/vector/array/type-change reflection and invalid input errors. |
| `visuals.shaders.varying` | Keep Python shader authoring and existing native compiler/reflection; expand SH packets only for a named missing interface. | Reuse stage-interface reflection; matching type/interpolation/location, invalid cross-stage interfaces and rendered interpolation. |
| `visuals.spectrogramvisual` | Preserve CPU FFT/window/hop pipeline over ImageVisual. | Known tone/time signal frequencies and scaling; window/step/data changes, then expected image. |
| `visuals.spherevisual` | Keep CPU sphere geometry generation over MeshVisual. | Radius/subdivision/shading changes, normals, topology and silhouette. |
| `visuals.surfaceplotvisual` | Reuse grid mesh geometry and shared shading. | Known height field, x/y/z/color mutations, normal recomputation and non-square grids. |
| `visuals.textvisual` | Reuse current SDF CPU helper/atlas/quad rendering and retained text corpus. | Glyph layout/kerning/anchor/rotation/font/style, atlas growth and exact lifetime; no font/SDK rebuild merely for docs. |
| `visuals.transforms.arg-to-array` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Retain CPU argument normalization; scalar/list/array shape/dtype and error behavior. |
| `visuals.transforms.arg-to-vec4` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Retain CPU conversion; defaults and homogeneous coordinates for 1D..4D inputs plus invalid shapes. |
| `visuals.transforms.as-vec4` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Reuse CPU vector conversion; expected padding/w values and array broadcasting. |
| `visuals.transforms.basetransform` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Keep map/imap/inverse/shader function contract; independent points and composed GPU transform. |
| `visuals.transforms.chaintransform` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Retain order/invalidation; noncommuting translate/scale/rotate plus append/pop and inverse. |
| `visuals.transforms.create-transform` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Retain factory selectors and arguments; exact concrete classes and invalid-selector errors. |
| `visuals.transforms.logtransform` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Reuse GLSL math/CPU counterpart; base/sign/domain boundaries and independently expected mapped coordinates. |
| `visuals.transforms.matrixtransform` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Reuse matrix uniform upload; translation/scale/rotation/projection, inverse, singular behavior and row/column order. |
| `visuals.transforms.nulltransform` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Retain identity on CPU/shader with all coordinate shapes; composition must preserve dimensions. |
| `visuals.transforms.panzoomtransform` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Reuse scale/translation path; map/imap after pan/zoom and transformed screen output. |
| `visuals.transforms.polartransform` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Keep polar math shader/CPU route; known radii/angles, inverse/domain seams and mapped output. |
| `visuals.transforms.sttransform` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Retain componentwise scale/translate uniforms; nonuniform/negative/zero scales and composition/inverse behavior. |
| `visuals.transforms.transformcache` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Keep identity/key invalidation; same chain reuse then mutation/reparenting invalidates without stale shader state. |
| `visuals.transforms.transformsystem` | Preserve the Python/GLSL transform implementation; change common uniform/compiler plumbing only on a failing vector. | Keep document/scene/canvas/framebuffer chains; pixel scale, clip, multiple views and coordinate round trips. |
| `visuals.tubevisual` | Keep CPU tube frames/tessellation over MeshVisual. | Bends/radii/closed path, frame continuity, colors and repeated data updates. |
| `visuals.visual` | Keep common draw/update/transform/filter orchestration. | Minimal concrete visual updates and draw hooks, freeze/unfreeze/state and resource cleanup. |
| `visuals.volumevisual` | Reuse existing native volume renderer/scientific admissions and installed volume suite. | Method/clim/interpolation/colormap/cutoff/step changes at fixed quality with independent captures; do not rerun performance until correct. |
| `visuals.windbarbvisual` | Inventory the actual expansion consumer, prefer existing CPU/instanced marker geometry before a new general geometry translator. | Known speed/direction/barb counts, scaling/rotation/mutation and clipped cases; SH-4 subset proof if needed. |
| `visuals.xyzaxisvisual` | Reuse line primitives with three fixed axis/color vectors. | Independent RGB axis orientation/length under camera and transform changes. |

## Shared native gaps: cheapest faithful implementation decisions

These mechanism packets unblock multiple API keys. Start with a small compiler/
CPU feasibility case and independently authored output oracle, then change the
shared native code once. Do not choose an easy subset and label the whole parent
complete. Keep unsupported legal inputs explicit until the full selected packet
passes its required profiles and exact-artifact gates.

| Key / gap | First route to evaluate | Stop / decisive check | APIs primarily unblocked |
| --- | --- | --- | --- |
| STATE dither | Determine the pinned format-specific observable allowance first; use an existing backend guarantee only if it satisfies that contract, otherwise evaluate an explicit output-stage lowering. | Quantization gradient with enable/disable and independent expected/tolerance rules. An arbitrary pattern or unexplained no-op is insufficient. | raw gl state, wrappers, image/mesh output |
| STATE multisample disabled on four-sample storage | Evaluate a single-sample raster intermediate resolved/expanded into retained multisample attachments only if it preserves color/depth/stencil and subsequent operations. Prefer direct native semantics when available. | Toggle on the same actual four-sample target; edge coverage and depth/stencil discriminate storage from raster state. Do not claim a one-sample allocation as the result. | framebuffer/renderbuffer, all raster visuals |
| STATE fractional/large polygon offset | Check native bias representation against admitted depth format; investigate a shader depth correction only where derivatives/early tests and interpolation are preserved. | Fractional and boundary values must yield independently predicted visibility; integer rounding/clamping cannot silently change legal inputs. | raw gl, mesh/depth/shading |
| STATE mixed constant blend domains | First map RGB/alpha factors independently to native blend descriptors; if unsupported, assess a composition pass with precise destination/ordering semantics. | Unequal constant RGBA/source/destination values, separate equations and updates; no equal-channel fixtures hiding factor substitution. | gl/wrappers, alpha/color filters |
| STATE stencil/enums/formats | Complete a finite table against existing descriptor mappings; add exact missing enum translations before inventing a new pass. | Face-specific masks, wrap versus saturation, actual attachment formats and invalid-input state atomicity. | gl, framebuffer, mesh/clip/picking |
| SH-1 runtime sampler indexing | Evaluate static per-element bindings plus bounded switch selection; preserve stage uniformity, derivatives and resource counts. | Native reflection plus uniform/divergent runtime indices and sampling/filter/LOD outputs. Divergent implicit derivatives need a faithful design, not an eager-sampling shortcut. | Program, texture filters, image/volume consumers |
| SH-2 multidimensional arrays | Reuse ordered numeric-uniform shapes and static sampler leaves ([source controls](static-sampler-arrays.md)); expand other storage/interface classes explicitly. | Element order, nested indices, partial updates and cache identity. Uniform-only success does not admit attributes/storage buffers. | Program, shader Variable/ModularProgram |
| SH-3 matrix/array attributes | Expand to column/element locations in shared reflection/binding code with exact stride/divisor handling. | Separate/interleaved buffers, constants, instancing and expanded native limits; independent rendered transforms. | VertexBuffer, instanced mesh/shading |
| SH-4 named geometry consumers | Inventory the actual visual/filter then prefer existing CPU tessellation or instanced expansion when its public contract allows; compute expansion only when needed. | Topology/interpolation/provoking/clipping/depth/side effects, updates and loss. Consumer rewrites do not admit arbitrary geometry programs. | wireframe/windbarb/arrow and any discovered geometry consumer |
| SH-5 generated-line side effects | Keep guards while classifying the exact evaluator; reuse ordinary line evaluation where it preserves execution count, otherwise design the required staged ordering. | Covered/clipped/degenerate inputs, early/late tests and atomic/storage effects. Native compilation alone does not remove the guard. | LineVisual, generated line consumers |
| Linux MSAA odd-size scissor | Reduce to the retained headless case with odd 301x177 size/nonzero origin, then inspect viewport/scissor/resolve coordinate conversion once. | Same independent edge expectation before/after on actual four-sample storage. Tk changes and shader-discard masking do not fix this runtime defect. | readback/framebuffer and affected raster workflows |
| Windows threedee OLE/RPC | Reuse exact failed environment/artifact; compare debugger/observer and stock Qt/Vulkan paths one variable at a time. | Existing three diagnostic + one causal confirmation budget, stack/wait-chain, actual exit/wait and retained failures. Favorable retries or disabling drag/drop cannot close it. | mandatory napari-threedee host row |

## First actions and cost limits

1. Read the selected row and its existing tests/receipts. Run the smallest decisive
   vector against the retained matching native leaf before editing anything.
2. Classify the result: missing method inventory, missing evidence, concrete
   implementation defect, unavailable runtime/hardware, or unsupported mechanism.
   An explained gap still prevents full closure, but each class has a different
   next action; do not rebuild native code to fix a missing report.
3. Fix a shared primitive and test its directly affected consumer keys. Reuse
   package/member and observer results only at their exact immutable identities.
   Pure layout/math/geometry changes normally need CPU and affected render vectors;
   changed native code needs one leaf build per affected ABI/platform configuration.
4. Batch coherent reviewed edits before expensive wheel/CI work. A failed control
   gets one causal correction and affected rerun; a repeated observation timeout
   polls the same live handle. No unbounded retry loops or duplicated SDK histories.
5. Finish each actual run with retained source/evidence/licenses/failure reproducer
   and exact managed cleanup. For a read-only/document or in-memory source check
   creating no scratch, record that fact rather than creating a fake build lease.

The original seed is not an exhaustive API inventory. Unseeded wrappers (including
submission/raster wrappers), method/value variants, wildcard scene aliases,
examples, events, shader hooks and additional hosts remain required reconciliation.
A new public key must get a concrete route and mapped obligation; it cannot be
silently treated as covered because it resembles a table entry.
