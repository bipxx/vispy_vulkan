# API method, alias and workflow reconciliation

## Current seven-row reconciliation — 2026-11-13

[Audit708](../compat/api-acceptance/scientific-current-dispositions-v2.json)
checks the two current44-case JUnit reports, both camera packets, six current
Qt rows and their original seven-stage functional/collector/worker reports.
It verifies33input hashes without running graphics or reinstalling packages.
Scope is runtime `2b8bccd`, Windows `9e4e30cc…`, WSL `a2715d26…`; these are
local installed observations, not final admission/public delivery. The initial
707audit adapter expected the wrong literal collector status; its exit1and
reproducer remain retained.708checks the inspected exact collector and worker
statuses and exits0/awaited. No runtime failure or verifier change is implied.

E03addition, 2026-11-14: the six new color/alpha composition cases below are
separately evidenced by712/713, not retroactively included in708's earlier
record-only audit. Both new test consumers use unchanged current wheel/runtime
bytes; their post-head test source has no final CI/admission transfer.

| Row | Public route / selected behavior | Current disposition and next missing claim |
| --- | --- | --- |
| U05 | Indexed/instanced `Program.draw`, source IDs, divisors and revisions | Eight rendered point references plus two controls pass per current wheel. Seven rendered routes are public; `nonzero_first_queue` is explicitly internal. Additional layouts/types/divisors/mutations stay open. |
| E03 | TextureFilter / PlanesClipper revisions; Alpha / ColorFilter composition | Four original pending-filter revision cases plus six selected color/alpha/texture/clip cases pass per current wheel. [Windows712](../compat/api-acceptance/mesh-color-alpha-windows-v1.json), [WSL713](../compat/api-acceptance/mesh-color-alpha-wsl-v1.json). General ordering, blending, MSAA and other supported compositions remain open. |
| E04 | Two fixed3Dscene controls; public TurntableCamera azimuth/center setters | Both fixed scenes and two mutation/restoration cases pass per wheel. Independent upstream reference covers the original/restored pose; fresh-scene equivalence covers changed poses. Other cameras/fov/events/plane/depth/stencil interactions remain open. |
| Q11 | MSAA capture format/sample/depth/stencil cells | Open LIF-05capability scope. Existing color resolve is not broad depth/stencil capture. Select named cells; this is not a volume row. |
| Q12 | Plain QWidget show/parent/resize, capture/update/ownership, hide/restore, injected recovery and close | Six current Windows/WSL PyQt5/PyQt6/PySide6 observations pass seven stages each. Final exact CI/profile admission/integration/delivery remain separate. No physical Linux GPU or Metal graphics transfer. |
| Q13 | Toolkit event/coordinate forwarding | QWidget overlay interaction alone does not qualify all keys, wheel, focus, mouse or timers. Select missing delivered-event routes under LIF-06; physical HID/touch/stylus/gestures/layout breadth remains separate. Not a volume row. |
| H03 | Glue invalidation-before-update protocol | Corrected upstream reference admission is historical. Renew only for a selected exact current host/version/binding rendered-mutation workflow under HOST-06. |

This closes the seven-row record reconciliation task. It does not close the
underlying broad API/scientific/host obligations. The142original obligations,
984unreviewed operation groups, original stock failures and frozen historical
admissions remain unchanged. Reopen a disposition when its route, values,
artifact/profile or chosen product claim changes.

Discovery checkpoint: 2026-11-07, source base `02a3839f` plus three docstring corrections.
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
| Event models / app.keyevent, app.mouseevent and non-root helpers | Mouse/key/resize/draw/scene payloads, histories, source/flag properties and emitter dispatch. | The finite installed CPU acceptance below covers 38 discovered groups/62 aliases plus utility dispatch/key helpers. | Physical delivery/normalization, general value domains, cyclic histories, picking and broader camera/scene interaction remain separate. |
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

### Finite installed event-model acceptance

The [event value record](../compat/api-acceptance/event-values-v1.json) overlays
finite CPU observations on 38 discovered operation groups / 62 visible aliases.
It records exact values and limits; it does not change the immutable catalog's
984 `unreviewed` entries or admit either original parent. Utility `Event`,
`EventEmitter`, `EmitterGroup` and `Key` helpers supplement that catalog.

All 57 cases pass without skips on each exact current wheel: Windows `5cb463cd`
and WSL Linux `b4c72484`. Thirty new cases complement 27 shipped emitter/key
cases. Each child checks 537 installed members and all loaded VisPy origins
(180 Windows / 179 WSL). The renderer module and GUI backend modules do not load;
a CPU SDF helper loads transitively from the checked installed package. The new
tests prohibit Application, Canvas and Timer construction. No device, rendering,
physical delivery, DPI or strict profile claim follows from this CPU scope.

| Family | Observed finite values and behavior | Explicit boundary |
| --- | --- | --- |
| Mouse payload | Default position/delta; buttons None/1/2/3; float position/delta copies; modifier tuple; native/custom payload identity. Invalid string/object buttons reject and valid construction recovers. | The caller's button list remains shared. Arbitrary shapes, button codes and backend normalization are not accepted here. |
| Drag history | Finite press plus two moves; raw press/last identity; non-drag returns None. `drag_events()` excludes the press and `trail()` truncates to integer coordinates. | No cyclic chain, physical pointer delivery or subpixel-trail preservation claim. |
| Key payload | Enter/A/None; empty, case-sensitive and Unicode text; modifier/native identity. String key aliases ignore case; character comparison uses uppercase ASCII65, not97. Invalid dictionary comparison rejects and later comparison works. | No OS key/text translation or arbitrary alternate-primary Key-object equality claim. |
| Resize/draw | Logical (30,20), physical (60,40) or logical fallback; draw region None/(1,2,3,4); native identity. | `ResizeEvent` requires an iterable size: its default None and integer size reject with TypeError. No delivered DPI/resize assertion. |
| Dispatch/group | Source stacks and flags on six models; handled continues, blocked stops; callback exception restores source stack, disconnect/re-emission recovers. Dynamic group names, collision preflight, block/unblock and disconnect work. | Group auto-connect and arbitrary type-failure atomicity remain outside the new finite group scope. Shipped tests add ordering/blocker/reentrance cases. |
| Scene wrapper | Two literal CPU affine mappings, cached position and visual reassignment; raw history/payload forwarding; missing scale refusal then valid1.25. | Copy shares raw event/visual but resets flags/source stack. Wrapper native is None; raw native remains available. Historical wrapper type, picking and general transform behavior are not qualified here. |

[Windows evidence](../build/runs/event-installed-windows-387/external-evidence.json),
[WSL evidence](../build/runs/event-installed-wsl-388/external-evidence.json).
Both isolated targets were removed after retaining results and rehashing 15/20
entries respectively; 45,644,393 scratch bytes were reclaimed. Existing wheels
and dependencies were reused without a native build or new environment. API-05,
API-06 profile admission and physical input LIF-06 remain open.

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

## Finite installed Tk delivery acceptance

[Tk input scope](../compat/api-acceptance/tk-input-v1.json) records 39 passing
cases per current v2 wheel on Windows Tk 8.6/RTX Vulkan and WSL Tk 9/software
Vulkan. Of these, 22 are explicit synthetic adapter vectors and 17 use
toolkit-generated delivery; three of the latter assert independent rendered
PanZoom/Turntable landmarks. Controlled-clock double-click cases are included.

The two new routing cases exercise actual focus transfer between embedded
canvases and a host Entry, including cancellation, native widget attribution,
host binding/text preservation and subsequent recovery. A delivered key-release
callback failure clears cached keys/modifiers and permits the next key pair.
Each child verifies all 537 installed members and its loaded VisPy origins;
all ten tracked resource gauges are zero after shutdown. Both scratch targets
are removed and evidence rehashed. No native build or new environment was used.

These observations close LIF-06-TK only. They do not establish physical-device
delivery, touch/stylus, Qt gestures, every keyboard layout, DPI behavior or
strict profile admission. The Tk adapter has no touch/stylus bindings in this
scope; the parent input obligation remains open.
