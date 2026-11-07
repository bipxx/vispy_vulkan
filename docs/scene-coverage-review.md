# Scene namespace review

Reviewed 2026-11-07 against source `dcf730bf`. This accounts for all **22 scene
seed parents** at source-route scope. It does not establish full method, shader,
event, clipping, picking or installed-artifact coverage. The canonical inventory,
its 142 original obligations and `reviewed=false` remain unchanged. API-05/06
retain reconciliation and acceptance of concrete workflows.

Scene code organizes nodes, transforms, cameras and visual wrappers above the
gloo/GLIR renderer. A Python class or alias being available does not prove its
generated shaders, target configuration or host event lifecycle works on Vulkan.
Published v1 qualifications and the newer local Linux v2 observations keep their
original artifact/profile identities; none qualifies this whole namespace.

## All seed parents

Paths below are relative to `src/vispy/`.

| Parent | Source route and present behavior | Acceptance scope / remaining gap |
| --- | --- | --- |
| `scene.cameras` | `scene/cameras/__init__.py` exports seven camera classes and imports the `make_camera` factory. Seven classes also reach the root scene namespace through `__all__`. | Factory names and direct class construction differ. Delivered input, linked views and backend timer behavior need finite method/profile cases. |
| `scene.cameras.arcballcamera` | `scene/cameras/arcball.py:ArcballCamera`; quaternion-based orbit interaction through the 3D rotation/perspective base. | CPU construction/transform availability is distinct from mouse gestures, projection, resize and rendered depth/clip behavior. |
| `scene.cameras.basecamera` | `scene/cameras/base_camera.py:BaseCamera`; node transforms, viewbox event hookups, camera state and linking. | State properties, partial updates, link/unlink, viewbox reassignment and close/recovery need operation-level cases. |
| `scene.cameras.flycamera` | `scene/cameras/fly.py:FlyCamera`; perspective movement, key map and a timer created with `start=False`. | Import availability does not verify a live application timer, keyboard/mouse delivery, motion integration or stopping after close. |
| `scene.cameras.magnify1dcamera` | `scene/cameras/magnify.py:Magnify1DCamera`; specializes the magnification transform used by `MagnifyCamera`. | Direct class route only, not a factory string. Nonlinear shader transforms, interpolation and timer/resize behavior need selected rendered cases. |
| `scene.cameras.magnifycamera` | `scene/cameras/magnify.py:MagnifyCamera`; extends pan/zoom with a magnification pre-transform and smoothing timer; unsetting its viewbox stops that timer. | Direct class availability is not lens-shader or timer qualification. Actual timer delivery, lens edges and viewbox reassignment remain open. |
| `scene.cameras.make-camera` | `scene/cameras/_base.py:make_camera`; accepts `None`, `base`, `panzoom`, `perspective`, `turntable`, `fly`, `arcball`; forwards constructor arguments. Unknown keys raise `KeyError`. | `magnify` and `magnify1d` are not factory keys. `PerspectiveCamera` is a factory route without being one of the seven wildcard camera exports. |
| `scene.cameras.panzoomcamera` | `scene/cameras/panzoom.py:PanZoomCamera`; rect/aspect/flip state and 2D event-driven scale/translation. | Independent coordinate expectations, aspect/flip combinations, delivered gestures and linked views need finite cases. |
| `scene.cameras.turntablecamera` | `scene/cameras/turntable.py:TurntableCamera`; elevation/azimuth/roll orbit and perspective/orthographic projection. | Existing CPU rotation-matrix cases cover four orientations, not all gestures, projection ranges or rendered outputs. |
| `scene.filters` | `scene/__init__.py` aliases the actual `visuals.filters` module, including clipping, opacity, picking, mesh shading and other filters. | Generated shader hooks, combinations and detach/update behavior belong to API-04/05/06 and shader coverage, not this module alias. |
| `scene.node` | `scene/node.py:Node`; one weak parent reference, strong child list, topology events, inherited clippers and transform paths. `children` returns a copy. | Existing CPU mapping/reparenting checks cover an acyclic tree. Cyclic/rejected topology, opacity/clipping inheritance, delivered events and canvas/resource lifetimes need explicit cases. |
| `scene.scenecanvas` | `scene/canvas.py:SceneCanvas`; extends app Canvas with scene draw order, visibility traversal, mouse dispatch/picking and offscreen render. `render` pops its pushed FBO in `finally`. | Backend creation, nested FBO/viewport restoration, picking bytes, crop/scale, error/loss recovery and shared lifetimes require exact installed evidence. The local Tk capture workflow is narrower. |
| `scene.transforms` | `scene/__init__.py` aliases `visuals.transforms`; eight names in its `__all__` also reach root scene. CPU composition/mapping and shader transform functions are separate routes. | Nonlinear/log/polar/magnification shader consumers, invalid values, inverse behavior and transform updates need scoped cases. The `create_transform` helper is module-level, not a wildcard root export. |
| `scene.visuals` | `scene/visuals.py` generates classes by combining `VisualNode` with selected `visuals.*Visual` classes; `__all__` includes classes derived from `VisualNode`. | Generated aliases, `VisualNode`, `create_visual_node`, picking filters, opacity and clipper propagation expand beyond the seed. Each visual/shader route retains its own API-04/05/06 obligations. |
| `scene.widgets` | `scene/widgets/__init__.py` exports seven scene-layout/widget classes, also exposed at root scene. These are scene visuals, not native toolkit widgets. | The existing module introduction mentions buttons/sliders that are not these seven exports. Record this documentation correction with the next pure-source documentation batch. |
| `scene.widgets.axiswidget` | `scene/widgets/axis.py:AxisWidget`; owns an axis visual, computes ends and links its view transform to a ViewBox. | Ticks, orientation, labels, linked range changes and resize need independent output/event cases. |
| `scene.widgets.colorbarwidget` | `scene/widgets/colorbar.py:ColorBarWidget`; wraps `ColorBarVisual`, updates size on resize and forwards color-map/label/ticks/clim properties. | Constructor kwargs go to the visual, not generally to Widget. All orientations, text, range mutations and clipping need finite cases. |
| `scene.widgets.console` | `scene/widgets/console.py:Console`; wraps its own `ConsoleVisual`, with text writes/wrapping, clear, font/color and resize routes. | Its specialized text shader/buffers are not automatically covered by `TextVisual`. Scrolling, wrap, resize and repeated writes need rendered/lifetime cases. |
| `scene.widgets.grid` | `scene/widgets/grid.py:Grid`; kiwisolver constraints arrange child widgets with spans, stretches, limits and spacing; offers add-grid/add-view helpers. | Solver mutations, overlapping cells and remove/reparent ownership need method cases. `remove_widget` removes `_grid_widgets` entries and marks the solver dirty; it does not detach `widget.parent` or clear `_cells`. |
| `scene.widgets.label` | `scene/widgets/label.py:Label`; wraps `TextVisual`, places it at the widget center and forwards text; constructor kwargs go to TextVisual. | Fonts, glyph layout, rotation, mutation, resize and clipping require actual text/rendered cases. |
| `scene.widgets.viewbox` | `scene/widgets/viewbox.py:ViewBox`; creates a clipped SubScene, attaches/selects a camera and reparents added nodes into that scene. | `camera=None` actually constructs the base camera despite its current PanZoom docstring. Bounds aggregate direct children without their transforms; recursive/transformed bounds are not implemented here. Clipping, camera replacement and multi-view lifetime need finite acceptance. |
| `scene.widgets.widget` | `scene/widgets/widget.py:Widget`; compound scene visual with mesh background/border, rectangular extent, layout properties, child widgets and clipping. | Pixel geometry, nested clipping/layout, picking and mutation/error cleanup need installed output cases; a class export is not such evidence. |

## Method and alias reconciliation still required

The reviewed seed has no individual rows for the generated visual-node aliases,
wildcard transform aliases, `VisualNode`, `create_visual_node`, SubScene,
`SceneMouseEvent`, camera perspective bases or module-level transform helpers.
The source audit records all 37 generated visual aliases and root exports; these
remain API-05 work rather than silently expanding or removing required seed rows.

For API-05/06, take one representative scientific scene through creation,
reparent/transform mutation, view/camera changes, clipping/picking, resize,
error/recovery and close on an exact installed profile. Give other routes a
concrete supported subset or explicit disposition. Keep timer-driven cameras and
the Console's specialized renderer separate from ordinary camera/text claims.
Reconcile the two stale widget/ViewBox descriptions in a single documentation
batch before the next shipping pure-source freeze; the audit itself changes no
shipping code and warrants no wheel or native rebuild.

Source accounting and CPU evidence are recorded in
[the scene audit](../build/runs/scene-audit-360/external-evidence.json). Existing
CPU node-transform, camera-matrix and transform-library tests pass all 15 cases
without skips on Windows and WSL. Additional probes verify namespace identity,
factory boundaries, ViewBox default/direct-child bounds and Grid removal's
retained parent. Neither run imports the native GPU module or constructs an
application, canvas or timer. The first WSL attempt's pytest file-capture error is
preserved; the successful retry changes only capture mode to `--capture=sys`.
[CPU retry evidence](../build/runs/scene-cpu-361/external-evidence.json).
These checks support only their named operations. No scene-wide functional or
release admission is claimed.
