# Tk raster capabilities and configuration

This records the standalone and supplied-parent contracts for `_dawn_tk.py`.
It refines TK-1/5/6 and BACKEND-2; it is source-functional evidence, not an
installed-wheel admission. The canonical compatibility ledger remains
`compat/vispy-compatibility.json`, with its full generated inventory unreviewed.
Relevant existing feature IDs are `app.backend.tkinter`, `app.canvas`,
`app.timer`, `gloo.glcontext`, `gloo.program` and `gloo.texture2d`.

Tk owns RGB presentation; Vulkan owns render/capture storage. There is no native
OpenGL context or context-interoperation promise. In the table, a host-controlled
option does not change the supplied parent's window or layout. An unsupported
request raises contextually; it is not counted as full upstream compatibility.

## Window and ownership contracts

The new fixtures are in
[test_tkinter_capabilities.py](../tests/native/test_tkinter_capabilities.py).
Existing lifecycle/input/capture coverage remains in
[test_tkinter_backend.py](../tests/native/test_tkinter_backend.py) and
[test_tkinter_capture.py](../tests/native/test_tkinter_capture.py).

| Public option/property | Standalone Toplevel | Supplied-parent Canvas | Fixture / restriction |
| --- | --- | --- | --- |
| `title` | Constructor and setter reach the Toplevel title. | Public metadata only; the host's title is unchanged, consistent with widget title semantics. | `test_standalone_window_options_and_mutations_reach_native_widget`; owner-thread title rejection preserves public metadata. |
| `size` | A geometry request; positive Configure dimensions report the actual client size. | Configures requested widget size; the host geometry manager controls granted size. | Standalone option fixture; existing resize/embedding/capture fixtures. Default backend scale is 1; nondefault public `px_scale` remains a separate contract. |
| `position` | Geometry request; getter reads Tk's acknowledged position. | Constructor request or setter raises before changing the host's layout. | Standalone option fixture and embedded refusal/mutation fixtures. |
| `show` | Deiconify/withdraw the owned Toplevel. | Initial placement belongs to the host. Once placed, hide/show saves and restores pack/grid/place options; pack order uses a surviving following sibling. A new host placement supersedes saved placement. | Three manager cases, pack-order/repeated-call fixture, and `test_hidden_host_relayout_replaces_saved_placement`. Other managers require host control and fail contextually. |
| `vsync` | `True` is refused; Tk raster presentation does not control scanout synchronization. | Same. | Configuration preflight; existing backend capability remains false. No optical latency claim. |
| `resizable` | Constructor sets the Toplevel policy. | Defaults are host-controlled; requesting `False` raises. | Standalone native policy check; embedded constructor refusal. No public mutable Canvas property is invented. |
| `decorate` | Constructor sets overrideredirect. | Defaults are host-controlled; requesting `False` raises. | Same fixture groups. |
| `fullscreen` | Boolean request goes to Tk. Getter reports the native acknowledged flag, separately from the pending request. | `True` raises; `False` reports no child fullscreen and does not change the host window. | `test_fullscreen_property_reports_native_acknowledgement` toggles both ways on Windows/WSL. Monitor-index requests remain unsupported. |
| `always_on_top` | Forwarded as Tk's topmost hint, as the public option's “try” contract requires. | `True` raises; the host owns window stacking. | Standalone option path and embedded refusal. Physical compositor stacking is not qualified by this packet. |
| `parent` | VisPy owns its Toplevel and Canvas, subject to the existing root-adoption rules. | Host owns parent/interpreter and initial geometry placement; closing the canvas preserves host widgets/bindings. | Existing root/embedding tests plus new host binding/layout tests. |
| `context` / `shared` | VisPy resource sharing on the shared native device. | Same, including two embedded consumers. | Four sharing cases: red output on both, shared texture update to green on both, close either first, update survivor to blue, then retire resources. This is not GL context interoperation. |
| `multi_window` | Multiple canvases have independent targets and lifecycle. | Multiple widgets may share a host interpreter. | Sharing and existing multi-canvas/application tests; no cross-thread toolkit ownership implied. |
| `scroll` | Platform-specific translation from the existing TK-6 contract. | Same; host bindings remain independent. | Existing fractional Windows delta, Linux button 4/5, modifiers and routing fixtures. Physical devices/layouts remain separately scoped. |
| capture | Renderer framebuffer/canvas capture. | Captures the canvas, not surrounding host widgets. | Existing asymmetric/alpha/crop capture fixtures. WSL toolkit/capture restrictions remain open; this packet does not transfer Windows capture evidence. |

## Requested and granted framebuffer configuration

Preflight runs before parent adoption, interpreter/widget creation or native
canvas registration. A failed request leaves `Canvas._backend` unset; the caller
can correct the context request and retry `create_native()`. Configuration
values supplied to `GLContext` are copied as original explicit-request
provenance. The merged `context.config` remains the requested configuration;
`gloo.get_gl_configuration()` reports actual storage. They are not interchangeable.

| Request | Admitted request / actual grant | Fixture / remaining scope |
| --- | --- | --- |
| `red_size`, `green_size`, `blue_size`, `alpha_size` | Integer minimum 0..8; actual RGBA8 storage grants 8 per channel. Boolean, negative and larger precision requests are refused. | Unsupported preflight cases and requested/granted cases. Alpha capture remains RGBA; Tk display is opaque RGB. |
| `depth_size` | Integer minimum 0..24; actual depth24plus-stencil8 guarantees at least 24. Exact depth precision stays unknown in the public configuration. | 0/16/default requests and refusal of 32. No invented 32-bit depth guarantee. |
| `stencil_size` | Integer minimum 0..8; actual stencil storage is 8 bits. | Default/8 requests and refusal of 16. Requesting zero does not remove shared backing storage. |
| `samples` | Integer 0 or 1 selects single-sample storage; 4 selects actual four-sample storage. Other values and booleans are refused. | Requested/granted cases assert native sample_count, including 1 and 4. Public `samples` uses its existing 0/4 convention. |
| `stereo` | False; True is refused. | Preflight refusal and actual false reporting. |
| `double_buffer` | Explicit False is admitted; explicit True is refused. The inherited upstream default True is treated as a legacy GL hint when omitted from the constructor request; actual native double_buffer is always reported False. Tk image replacement is not a native GL back buffer. | Both default and explicit-False actual reporting, explicit-True refusal and corrected-request retry. Native double-buffer compatibility remains unsupported. |

The minimum-bit and sample policy applies to both modes. Explicit config is
supplied at Canvas construction; mutating arbitrary private provenance is not a
supported configuration route. Active FBO configuration continues to come from
its actual allocated attachments, not these default-target request fields.

## UI thread and failure atomicity

Create an Application on the UI thread that owns its Tcl interpreter, and use
its canvas/application operations and timer lifecycle on that thread. An
existing shared root also records its attaching UI thread. The backend refuses
other threads before toolkit calls, scheduling, current-canvas selection or
native release. Host-created Tcl interpreters must be supplied from their owning
thread; this does not add arbitrary cross-thread Tk dispatch.

Canvas close/title and Timer start/stop/interval changes check the backend's
optional thread precondition before changing public state. Other backends keep
their existing route when no such precondition exists. In particular, a refused
timer stop leaves its running flag and scheduled job intact; a refused canvas
close leaves its closed flag/current-canvas bookkeeping intact. Seven worker
controls verify these properties, alongside a worker canvas-selection control.
The owner can subsequently stop/close normally.

## Evidence and open obligations

The first Windows run reproduces 20 failures, with four existing sharing cases
passing. The final packet contains 45 new capability cases within 328 Windows
and 314 WSL software affected cases; 47 CPU/source contracts also pass. Both
native profiles report all nine shutdown gauges zero. The existing native
candidates are reused by hash: no native build, wheel or environment was created.
Original upstream files/notices remain retained; Canvas/Timer changes are
explicitly recorded in `compat/deviations.txt`, and source-preservation checks pass.

These counts do not close full G0 mapping, independent implementation review,
installed-member/closure/observer gates, physical input/DPI/compositor behavior,
the Linux toolkit/scissor blockers or the mandatory threedee row. Earlier and
final Windows logs also retain an occasional Tcl ThemeChanged diagnostic for a
destroyed interpreter, seen before this packet; its attribution and complete
Tcl shutdown qualification remain open. Expected injected cleanup errors are
retained separately in the lifecycle suites. No source-test total qualifies an
installed Tk profile or eliminates a previously required compatibility row.


## Later shutdown/progress source checkpoint

The [shutdown and progress record](tkinter-shutdown-compatibility.md) attributes
and regression-covers the retained ThemeChanged diagnostic to a test host's
idle-before-destroy ordering. It also fixes duplicate native-progress error
reporting across scheduled draw and timer routes. Full affected source suites
pass 425 Windows/411 WSL cases with nine zero native gauges, plus 38 CPU/source
contracts. This supersedes the specific unattributed source observation above;
full Tcl lifecycle/installed qualification and all other restrictions stay open.
