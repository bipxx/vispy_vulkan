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
Viewport changes also update the Python context cache. `glFinish` waits through
the native implementation. Arbitrary object IDs, shader creation, raw draw calls
and `glFlush` remain unsupported; the existing GLIR flush operation alone would
not satisfy immediate `glFlush` submission semantics.

The existing public `gloo.flush()` also reaches the logging-only native flush
operation. Actual submit-without-completion-wait behavior for both APIs remains
an implementation requirement; it cannot be closed by relabeling the wrapper.

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
