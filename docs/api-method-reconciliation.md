# API method, alias and workflow reconciliation

Checkpoint: 2026-11-07, source base `02a3839f` plus three docstring corrections.
This extends the [implementation routes](api-implementation-routes.md) and four
namespace reviews. **API-05 remains open.** The source snapshot discovers
operations; it does not decide their supported values or discharge an original
parent. All canonical inventory and candidate-selection bytes remain unchanged,
including `reviewed=false` and every original obligation.

## What is now recorded

The retained catalog accounts for all 142 seed parents, treating 14 historical
backend-selector entries as selectors rather than trying to import fictitious
`vispy.app.backend.*` objects. It records 265 visible class/function aliases and
984 source operation groups: constructors, Python methods, properties with their
available accessors, module functions and selected operators. Inherited members
point to their defining implementation; aliases share that implementation
record. Parent links are retained where discovery establishes them.

The snapshot also includes the 37 generated scene visual classes through their
visible aliases/MROs, explicit non-root event/view/context helpers, all three
local examples, Canvas/Timer event declarations and the raw facade's state-call
allowlist. Windows and WSL produce the same catalog bytes. Each source file is
hashed once during discovery; constructor guards retain original definitions for
reflection while continuing to prohibit application/canvas/timer construction.

All 984 groups deliberately retain `acceptance=unreviewed`. They are neither
984 new mandatory tests nor 984 passing APIs. The snapshot's zero unresolved
source locations applies only to the chosen reflection rules. It excludes
arbitrary dynamic attributes, most constants, external/native descriptors and
operators outside its explicit list. Generated constructors expose factory
wrappers; their underlying visual signatures/values still need reconciliation.
Static example imports/calls do not resolve general instance-method dataflow or
prove example execution. These limits remain explicit in the catalog.

[Discovery and CPU evidence](../build/runs/api-reconciliation-367/external-evidence.json),
[original timeout/guard-discovery failure](../build/runs/api-reconciliation-366/external-evidence.json).

## Method families and the next faithful checks

This table prioritizes semantic work over the source-discovery list. A shared
implementation can serve several aliases, but each distinct observable and
required value/mode keeps its own acceptance obligation.

| Family / original ownership | Operations and aliases to reconcile | Existing route to reuse | Acceptance still needed |
| --- | --- | --- | --- |
| Application / app parents | Instance `create`, `run`, `process_events`, `quit`; module aliases and `use_app`. | Existing Application/default-app implementation and finite manual Tk pump. | Singleton/alias reuse, blocking versus manual loop, host ownership and repeated/error calls; instance proof does not qualify every module alias. |
| Canvas / app.canvas | Constructor/config, current/shared context, size/physical size, update/show/close and context-manager methods. | Existing Canvas/backend and Tk/Qt lifecycle suites. | Supported config/value tables, delivered resize/focus, close/error/loss and shared ownership on each claimed profile. |
| Timer / app.timer | Constructor/start/stop, interval/iterations/running, start/stop/timeout events. | Existing one-shot criterion plus native timer ordering tests. | Repeating/restart/interval changes, callback failure/stop and UI-thread delivery; event declaration is insufficient. |
| Context / gloo.glcontext | Current selection, shared namespace, GLIR flush, config and `GLShared` extension methods. | Existing shared GLIR/parser and two-canvas scenarios. | Direct-constructor forms, namespace/owner identity, ordering and loss/close behavior. |
| Objects/buffers / gloo parents | `delete`, `set_data`, subdata/indexed assignment, views, dtype/stride/divisor and operators. | Existing upload/retirement mechanism and indexed/instanced tests. | Value/layout bounds, alias/view update ordering, constants/matrices, rejection atomicity and survivor/resource retirement. |
| Textures/framebuffers / gloo parents | Data/subregion assignment, formats/filter/wrap, attachment/resize/read and activation operators. | Existing texture/FBO and finite capture mechanisms. | Typed sampler/format matrix, layers/MSAA, bounds, nesting/restoration, mutation/failure/recovery. |
| Program / gloo.program | Shader/uniform/attribute assignment, binding, draw, indexed/instanced inputs and deletion. | Existing shader/reflection/GLIR path. | Array/matrix/sampler variants and limits remain SHD-01–05; geometry shader availability is explicitly refused. |
| Raw facade / gloo.gl | `gl2`/`gl+` aliases, state/query/submission functions and wrapper equivalents. | Current Dawn facade and independent raw-versus-gloo submission/capture controls. | Reconcile operation/value support, counters and queue/state rejection. Exported proxy functions do not promise arbitrary raw object, shader or draw interoperability. Legal-state residuals remain STA-01. |
| Scene topology / scene parents | Parent/children, visibility/opacity/order, transforms, bounds, draw/picking, viewports/FBOs. | Existing Node/SceneCanvas and source/installed scene fixtures. | Actual topology/event/resource lifetimes and nested render/picking output. Acyclic CPU mapping does not test cyclic topology or all clipping/ownership paths. |
| Generated scene aliases / scene.visuals | 37 generated VisualNode classes, inherited visual operations, factory constructor, picking/filter behavior. | Preserve each class's underlying Visual plus the existing node wrapper. | Map forwarded arguments and inherited methods; wrapper import or one underlying visual does not qualify all aliases. |
| Cameras / scene.cameras | Factory keys, direct constructors, viewbox assignment, state/linking and delivered input. | Existing camera transforms and selected coordinate/gesture tests. | Base/PanZoom/Turntable routes, direct-only magnify cameras, timer-driven fly/magnify and actual input delivery require separate finite scopes. |
| Widgets / scene.widgets | Grid add/remove/resize, ViewBox camera/add/bounds, label/axis/colorbar/console mutation. | Existing compound visuals and solver. | Grid removal retains parent/cell references; ViewBox bounds are direct-child/untransformed. Give these explicit method dispositions. Specialized Console rendering is separate from TextVisual. |
| Visual data and scientific preparation / visual parents | `set_data`, bounds and visual-specific properties, preparation hooks and sharing/views. | Existing geometry/CPU preparation plus matched native visual fixtures. | Meaningful images for mutations/errors/recovery; extraction/layout passes are not renderer acceptance. SCI-01–06 remain visible. |
| Filters / visual filter parents | Attach/detach/order, enabled/material/texture/clip/picking properties and data updates. | Existing shader hooks; CPU ID packing and normalization checks. | Selected compositions, ID bytes with blend/depth controls, normal/instance transforms and lifecycle require rendered evidence. |
| Shader authors / visual shader parents | Functions/chains/statements, variables/varyings and ModularProgram/MultiProgram operations. | Existing CPU composition and ordered uniform/attribute implementation. | Native stage compilation, reflection, rebuild/error/ownership and supported shader forms. `StatementList` is public but omitted from wildcard `__all__`. |
| Transforms / visual transform parents | Mapping/inverse/composition, factory keys, cache and TransformSystem plus selected operators. | Existing CPU mapping tests and scene transform propagation. | Domains/shapes/dtypes, dynamic cache updates, framebuffer/pixel-scale and CPU-versus-shader expectations. |

## Event and backend additions

Canvas declares initialize, resize, draw, five mouse-related events, key press /
release, stylus, touch and close (13 names total). Its deprecated `paint` alias is
added separately and forwards draw events; the discovery's EmitterGroup-only list
does not include that alias. Timer declares start, stop and timeout. Public
submodule `ResizeEvent`, `DrawEvent` and `SceneMouseEvent` supplement the root
MouseEvent/KeyEvent seed entries. Preserve event values, native provenance,
logical/physical coordinates, drag history and callback order separately from
physical delivery. Keyboard, wheel, touch and focus requirements remain LIF-06.

`dawn_headless` is an additive shipping selector with its existing strict profile
history. `_test` also appears in the raw registration difference but is internal;
it is not a new shipping backend. The nine legacy selectors retain explicit
refusals. The notebook route exists but its optional runtime evidence must not
substitute for Tk/Qt profiles. No backend is imported merely to discover its
selector.

## Representative example bindings

The three maintained examples are linked to their actual existing test bodies.
The initial discovery kept them as source bindings. A later local installed run
now passes all three on Linux wheel `b4c72484`, source `c141eade`, CPython 3.12.13,
Tk 9.0 and pinned WSL software Vulkan. It verifies 537 package members and all 171
loaded VisPy Python-module origins in the example process, with ten zero shutdown
gauges. This is exact local functional evidence, not strict profile or parent
admission. [Installed observations](../build/runs/linux-current-installed-370/external-evidence.json).
The original discovery catalog keeps `executed=false`; its historical state is
not rewritten to represent the later observation.

| Example | Public method/value route | Existing decisive test body | Residual scope |
| --- | --- | --- | --- |
| `examples/tk_image_overlay.py` | SceneCanvas, PanZoomCamera, nearest/subdivide uint8 image, STTransform and agg Line; image/line updates, resize and camera rect. | `tests/native/test_tkinter_image_overlay.py::test_image_overlay_updates_recovery_resize_and_pan` checks independent RGBA/Tk landmarks, complex-data rejection, valid subsequent update and delivered drag after resize. | Bind its exact installed wheel/Tk/driver and shutdown evidence; not all image formats, line modes or DPI/input cases. |
| `examples/tk_mesh.py` | SceneCanvas, orthographic TurntableCamera, two float32/uint32 meshes with `shading=None`; vertex/color update and quarter-yaw drag. | `tests/native/test_tkinter_mesh.py::test_mesh_example_updates_and_quarter_yaw` checks projected literal landmarks before/after mutation and rotation. | Not all cameras, shading filters, instance layouts or depth/stencil combinations; retain SCI-02/03 and SHD-03. |
| `examples/tk_volume.py` | SceneCanvas, TurntableCamera, 32-cubed float32 `r32f` volume, nearest sampling, MIP and MINIP, data/method mutation. | `tests/native/test_tkinter_volume.py::test_volume_example_updates_methods_and_invalid_data` checks bright-block landmarks, invalid method/2D-data rejection and a valid subsequent update. | Not large-volume performance, all raycasting/interpolation modes, formats or devices; SCI-04 remains separate. |

Each example connects close and manually pumps `Application.process_events`,
then closes the canvas and quits in `finally`. That common source structure does
not independently qualify the loop or prove every close/error path.

## Public documentation corrections and evidence boundary

The visuals introduction now describes supported gloo/GLIR/Dawn rendering rather
than claiming it contains only OpenGL machinery. The widgets introduction lists
the scene-layout objects actually exported. ViewBox now documents its unchanged
`BaseCamera` default and the explicit `panzoom` choice. All three changes preserve
executable ASTs, original BSD headers and line endings, and are listed in
`compat/deviations.txt`.

Both platforms pass 58 existing CPU cases without skips, including the two source
identity/parity contracts. No GPU module is imported and no application, canvas
or timer is constructed. The first discovery attempt's WSL timeout and guard-
hidden constructors remain retained; the retry caches source metadata and uses
original constructor references without changing the 150-second limit or the
construction guards.

The coherent source batch is frozen at `c141eade` and packaged as Linux wheel
`b4c724842cbb8bfadb2097a025acd30cbdce006bad2b27b3b62b149cda398b69`.
Five description members differ from the original CI producer; all native and
notice bytes stay unchanged. Exact archive joins and manylinux_2_39 analysis
pass using the retained locked tools without new installation or native build.
The installed run passes 63 cases, eight Tk branches, four capture branches and
all five active rejection controls, including the three example tests above.
Existing Linux wheel `438ec1ce` and its results retain their original bytes and
scope. API-05 still requires semantic reconciliation; API-06 and release gates
still require the remaining exact profile evidence and independent admission.
