# Compatibility with upstream VisPy

The Vulkan implementation is not a complete upstream replacement. The
[installed matrix](../compat/no-opengl-matrix.json) describes selected application
profiles, not a percentage of supported VisPy features. Existing release wheels
and draft assets do not automatically acquire newer source features.

## New source features

Select `app.Canvas(app='tkinter', size=(640, 480), show=True)` to use Tkinter
without pyopengltk or an OpenGL context. Rendering uses the existing Vulkan
renderer; an owned Tk PhotoImage displays RGB readback. Capture through
`gloo.read_pixels(alpha=True)` retains RGBA. Embedded widgets use
`parent=<tk widget>`; pack/grid the returned `canvas.native` yourself. Display
pixels and Tk widget coordinates share the native Tk pixel dimensions. Toolkit
window-size limits still apply. Vsync and transparent window compositing are not
provided. This path transfers frames through CPU memory; it is not native Vulkan
window presentation.

Real Windows GPU and WSL software Vulkan integration tests cover drawing,
presentation orientation, resize, input, embedded/native widget destruction,
multiple canvases, timers, animation, callback recovery and device-loss recovery.
These source tests reuse existing native binaries. A new installed wheel and all
three no-OpenGL qualification gates are still required before adding a shipping
matrix row. Run `tests/native/test_tkinter_backend.py` with pytest `-s` to avoid
the observed interaction between Windows Tcl initialization and descriptor
capture; do not treat the earlier captured failures as a product fix.

The subsequent Astra review found Tk correctness gaps. Pressed-button tracking
now supports real PanZoom/Turntable camera drags in source tests and cancels
gestures on focus loss. Source regressions now also cover explicit-parent
NoDefaultRoot embedding, shared-interpreter application ownership, constructor
unwind and public timer stop/restart state. One Application rejects simultaneous
canvases on different Tcl interpreters; use a separate Application per interpreter.
Callback/native-progress source regressions now exercise manual pumping,
Application.run and externally owned mainloops. An escaping toolkit callback
failure is re-raised with its traceback by manual/VisPy-owned drivers; a borrowed
mainloop uses the user's existing report_callback_exception handler. The first
error is preserved, later errors are logged, and a failed timer stops. The
existing EventEmitter ignore policy is retained. A 5 ms interpreter progress
callback services native work when there is no redraw; it stops retrying after a
poll failure until explicit re-entry or redraw and is cancelled on release.
KeyboardInterrupt/SystemExit propagate through manual/VisPy-owned drivers.
Nested Application.run calls are rejected. These checks do not establish every
teardown failure path or installed qualification. Close now attempts backend
cleanup even after an escaping close-event failure; Timer.stop marks its public
state stopped after backend cancellation errors. Tk teardown attempts independent
resources and retains the first failure. Native IDs and scheduled-job handles
are cleared only after release or known interpreter destruction. Failed release
owners remain retained for an explicit application.quit retry, without an
automatic cleanup retry loop. Callbacks cannot create new Tk canvases/interpreters
or restart timers while that application is quitting. Broader lifecycle,
coordinate and capture acceptance remains open; see the [current specification](superpowers/specs/2026-10-24-vispy-compatibility-gap-closure.md).

Tk root ownership now has an explicit adoption rule: passing `parent=<tk widget>`
makes that interpreter host-owned, even when VisPy originally created it. The
host releases it with `root.destroy()` after its own work finishes. Reading
`application.native` alone does not transfer ownership. At final application
release, an otherwise managed root is also preserved if it still contains
unrelated child widgets, scheduled callbacks, root bindings or new Tcl commands
(including namespaced commands and variable-trace callbacks). VisPy removes its
own callbacks, binding, images and native resources without dispatching host idle
work. Old VisPy image wrappers do not accidentally retain an otherwise exclusive
root. Use an explicit parent for opaque Tcl state whose ownership cannot be
inferred from those remaining resources.

Tk input now preserves native event objects and double-click position, button,
held buttons and modifiers. It uses the pinned base detector: consecutive
presses of the same button at the same widget position within 0.3 seconds emit
a double-click in addition to ordinary presses/releases. Focus loss clears
gesture/click history and held modifier/key state. Left/right modifier aliases
are tracked independently; Windows-key and Super aliases map to META. Printable
Unicode/keypad text is distinct from navigation/control keys, and releases retain
the corresponding press identity/text when Tk supplies no usable release text.
The admitted named function-key range is F1–F12; other unknown symbols without
printable text emit an unknown key with empty text and retain their native event.

Windows MouseWheel deltas retain fractional ticks in units of 120; Linux button
4/5 events produce vertical wheel ticks without creating held mouse buttons.
X11 mask translation assumes the default Mod1 Alt/Mod4 Super layout. Arbitrary
remapped layouts, physical device delivery and macOS remain unqualified; synthetic
translation vectors are not hardware evidence. Two embedded canvases route input
independently while preserving their host's bindings.

Focus-loss cancellation completes releases and clears gesture state even when
a release callback raises, then delivers the first failure through the existing
loop error route. Another held button cannot become a stuck drag after that error.

This input packet adds 30 source cases. The final affected suites pass 130 cases
on Windows and 116 on WSL software Vulkan, with all nine native shutdown gauges
zero. These counts include prior lifecycle/camera tests; Windows also includes
capture. The separately failing Linux capture workflows remain open. No native
rebuild, new wheel, installed-profile promotion or hardware-input claim follows.

This ownership packet has 100 passing Windows Tk/state/capture source cases and
86 passing WSL Tk/state cases, plus 12 packaging/source contracts. The WSL count
excludes the separately failing expanded capture workflows below. These results
reuse existing native artifacts and do not qualify a new installed wheel.

Independent Windows capture tests now verify known corner colors across odd-size
resize/device loss, single/four samples, fractional alpha, cropped float/byte
readback, embedded capture and Tcl image replacement. Local Tk scaling settings
preserve widget/event pixel coordinates without a second framebuffer scale;
this does not qualify OS mixed-monitor DPI changes. Monitor-index fullscreen is
explicitly unsupported; pass a bool for Tk fullscreen.

The new Linux capture tests remain incomplete: an exact four-sample boundary
after resize differs from its independent expectation, and Tk Label construction
aborts with an Xlib/XCB sequence assertion in the current WSL runtime. The latter
also reproduces in plain Tk without VisPy/Vulkan. Neither the toolkit failure
nor the pixel mismatch is hidden by skips or relaxed expectations. Windows
results and earlier Linux source tests do not qualify this expanded workflow.

Selected `gloo.gl` state calls now execute through the current canvas's ordered
GLIR queue: viewport/scissor, clear color/depth/stencil and clear, masks,
enable/disable, depth range/function, front/cull face, line width, polygon offset,
blend and stencil state, sample coverage, and `glFinish`. Native validation still
rejects unsupported values or configurations. Prior queued gloo work is processed
before each raw state operation, preserving ordering and framebuffer selection.
Viewport changes also update the Python context cache. Matching new native
candidates implement both `gloo.flush()` and `gloo.gl.glFlush()` through real
current-canvas submission without a deliberate completion wait. Empty/repeated
flushes with no new work are no-ops. The bounded in-flight ring reports a
contextual capacity error if it cannot submit the promised work; pending work is
retained for `process_events()` followed by an explicit retry. A capacity error
is not a successful flush, and no unlimited queueing contract is claimed.
The parser rejects flush on older native modules lacking submission contract
version 1, so their historical logging-only route cannot silently pass.

`gloo.finish()`/raw `glFinish` complete preceding work without requesting GUI
drawing or presentation, preserving active framebuffer, viewport and scissor.
Native readback no longer requests presentation either. Explicit presentation
still copies a previously completed target when there are no new draws.
Submitted owners are retained before Queue.Submit; post-submit failures cannot
replay consumed work or free owners early. Query-frame submission counts commit
at the actual submit boundary before optional callback/map bookkeeping.
Arbitrary immediate object IDs, shader creation and raw draws remain unsupported.

The native submission packet has 168 passing Windows source cases, 146 passing
WSL software cases, 67 CPU/source contracts and a passing C++ frame-lifecycle
contract. Separate Linux scissor testing still passes seven cases and fails one,
now explicitly verifying that four samples were granted. These are functional
candidate results, not installed-wheel/absence qualification. Windows reuses the
verified vendor SDK; the experimental Linux leaf reuses retained libraries and
recompiles all first-party units with the producer's GCC version, using portable
headers from the existing pinned nanobind 3.1.0 environment. Exact wheel packaging,
complete member/profile audits and all three observer gates remain pending.

## Remaining gaps

- Windows napari-threedee startup remains intermittently blocked in OLE window
  registration. A successful retry is not proof of a fix.
- GLFW, SDL2, pyglet, wx, EGL/OSMesa and older Qt backends remain unported in the
  strict package. Original implementations remain excluded and available as
  source references. Qt support uses the pinned selected profiles.
- Shader compatibility still excludes arbitrary geometry stages, dynamic
  sampler-array indices, multidimensional arrays and some vertex attribute
  types/line-evaluator side effects. Explicit failures are not completed ports.
- Full upstream visual/example coverage and performance parity are not yet
  established. Bounded functional tests do not prove arbitrary shader or driver
  compatibility. Linux software pixels can differ from NVIDIA references.
- Native Linux GPU qualification needs a suitable GPU host. macOS Metal remains
  experimental and needs Mac hardware. No Mac is currently available.

Follow the [gap-closure plan](superpowers/plans/2026-10-24-vispy-compatibility-gaps.md)
and [build hygiene policy](build-hygiene.md) for subsequent implementation.
