# Experimental native Tk presentation

The updated source supports an explicit native Vulkan presentation mode for Tk
on Windows and Linux/X11. Raster remains the default. Qt is not required by
either Tk route. The new experimental `0.17.0+vulkan.2` wheels contain this
feature; the published v1 release does not. Independent review and strict
release qualification of the new wheels remain pending.

```python
from vispy import app, gloo

application = app.Application('tkinter')
canvas = app.Canvas(
    app=application,
    size=(640, 480),
    show=False,
    vsync=True,
    backend_kwargs={'presentation': 'native'},
)

@canvas.events.draw.connect
def draw(event):
    gloo.set_viewport(0, 0, *canvas.physical_size)
    gloo.clear(color=(0.1, 0.3, 0.5, 1.0))

canvas.show()
try:
    application.run()
finally:
    application.quit()
```

This example requires the updated source/package. Choose
`backend_kwargs={'presentation': 'raster'}` or omit that option to retain Tk's
RGB image presentation. Raster continues to reject `vsync=True`. Native mode
forwards the vsync request to the existing renderer; compositor scheduling and
physical scanout timing are not certified here. Native failures are explicit;
there is no silent switch to raster after a native request.

## Implementation

- Native mode uses a dedicated Tk frame and the renderer's existing Win32/Xlib
  surface API. Its presentation callback does not perform `read_pixels` or
  allocate a `PhotoImage`; explicit framebuffer capture remains available.
- Map attaches/configures the surface; unmap retires it and pauses its extent.
  Resize, input bindings and device-loss reconstruction reuse existing routes.
- Tk must finish pending X11 window creation/display work before the renderer
  validates the XID through its own display connection. Idle callbacks can
  close or hide the widget, so attachment rechecks its lifetime and visibility
  and rereads the handle after processing those callbacks.
- Python widget destruction retires the renderer before destroying the borrowed
  native window. A failed retirement preserves the live window and pending owner
  for explicit retry. Arbitrary raw Tcl/OS destruction is not qualified here.
- No native renderer, SDK, driver or dependency environment was rebuilt.

## Driver and platform limits

The prototype is bounded to Windows Vulkan and Linux Tk using X11. Native mode
is refused on macOS; Metal remains experimental. There is no native Wayland
claim. Fractional DPI, cross-monitor migration, touch/stylus, transparent
composition, embedding variants and all sample/format combinations remain
separate work. The current surface-scale setting is 1.0.

The project's recent clipping-test Mesa driver was deliberately built with
`-Dplatforms=[]`; it supports headless software Vulkan and cannot present to
X11. Those identities and results remain unchanged. X11 prototype tests instead
select the existing system `mesa-vulkan-drivers` package
`25.2.8-0ubuntu0.24.04.2`, with explicit ICD and library hashes retained in the
test record. This separate software driver does not inherit the headless
driver's clipping evidence or qualify native Linux hardware. Global driver
settings are not changed.

## Verification scope

The prototype suite is
[`tests/experimental/test_tkinter_native_presentation.py`](../tests/experimental/test_tkinter_native_presentation.py).
It stays separate from the mandatory `tests/native` CI scope; an optional Tk
native test does not create a Metal or headless-driver release obligation.

Eight cases cover:

1. Native presentation with vsync requested off/on, independent green pixels,
   actual one-present completion receipts, and prohibited `PhotoImage` creation.
2. Resize, hide/restore and delivered mouse coordinates.
3. Python widget destruction after surface retirement.
4. Injected retirement failure, preserved live window, and successful retry.
5. Device-loss recovery on the same widget.
6. Invalid mode rejection before creating a Tk root.
7. Closing the canvas in an X11 idle callback prevents stale surface attachment.

The two vsync parameters make eight cases. Source `b38c4f90` is packaged in
Windows wheel `a86b030b…` and Linux wheel `48164e05…`. Each normal offline
installation verifies all 537 package members with zero source overrides.
Both platforms pass 130 native/raster cases (eight new and 122 existing), plus
56 state/capture cases, with no skips. Functional validators and five active
capture corruption controls also pass their expected outcomes.

WSL uses the existing system Mesa 25 driver for native X11 tests and the pinned
patched headless Mesa 26 driver for raster state/capture checks, selected per
child process. Mesa 25 failed one exact MSAA resize raster case; that failure is
retained without relaxing its tolerance. A subsequent capture harness still
referenced an older wheel; its failed attempts are preserved, and all six
capture processes were rerun against the correct installed artifact.

Exact source, drivers, outcomes, failures and cleanup are tracked by the
[installed-wheel packet](../compat/api-acceptance/tk-native-installed-v1.json).
The earlier [prototype packet](../compat/api-acceptance/tk-native-prototype-v1.json)
retains its historical source-overlay scope. Only the Python backend and wheel
RECORD changed; native binaries and original license notices are unchanged.
The [new candidate packet](../compat/candidates/tk-v2-native/review-packet.json)
renews preparation for these artifacts. Existing approvals do not transfer;
independent review and strict installed/profile admission remain open.
