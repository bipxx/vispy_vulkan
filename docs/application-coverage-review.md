# Application namespace review

Reviewed 2026-11-07 against source `fa72c6dadba526faf5676b7d580e7d555e5dd487`.
This accounts for all **25 application parents** in the seed inventory at the
source-route level. It does not qualify their complete method/value surfaces.
The canonical inventory remains `reviewed=false`; API-02 through API-06 remain
separate work. No original feature/profile obligation or candidate selection is
removed by this review.

The seed's `app.backend.*` entries identify backend selectors. Their operative
public route is `Application(backend_name=...)` or `use_app(...)`, rather than an
importable `vispy.app.backend` module. Preserve those IDs when reconciling methods
and routes under API-05.

## Evidence and limits

The last published v1 release qualifies the selected Windows/WSL headless and
plain-QWidget readback profiles, plus finite Tk criteria. See the exact artifact
identities in [the coverage checklist](coverage-checklist.md). This review grants
no v2 installed qualification, no general Qt/native-presentation qualification
and no macOS graphics claim. Metal remains experimental.

The source routes below are in `src/vispy/app/`. The new compiler-free boundary
tests use public `Application`, `MouseEvent` and `KeyEvent` calls. They cover all
nine removed selectors through explicit and configured selection, unknown names,
key payloads and an ordered mouse drag chain. They verify that refused selections
load no additional removed-toolkit modules. They do not create a native application
or prove physical input delivery. The tests are registered in the curated CPU
suite. Durable results and exact source hashes are referenced from the checklist.

## All seed parents

| Parent | Source route and present disposition | Acceptance scope / remaining gap |
| --- | --- | --- |
| `app.application` | `application.py:Application`; selects a backend, with lazy native application creation. | Finite Tk evidence covers manual progress and host-preserving quit. Review automatic selection, interactive/gallery paths and complete application lifetime separately. |
| `app.backend.egl` | Selector `egl` is explicitly refused before backend import. | Source-tested refusal; no EGL application/presentation support claim. |
| `app.backend.glfw` | Selector `glfw` is explicitly refused before backend import. | Source-tested refusal; a future port needs no-GL window creation and its own presentation/lifetime qualification. |
| `app.backend.jupyter-rfb` | Registry `jupyter_rfb` loads `_jupyter_rfb.py`; `_offscreen_util.py` creates a Dawn headless canvas and framebuffer helper. | Reachable optional implementation, not selected release qualification. Async-loop processing, widget events/resize, framebuffer delivery and close/reopen need a real notebook run. Hide/position and supplied-parent limitations remain explicit. |
| `app.backend.osmesa` | Selector `osmesa` is explicitly refused before backend import. | Source-tested refusal. Use the selected Dawn headless route for supported offscreen workflows. |
| `app.backend.pyglet` | Selector `pyglet` is explicitly refused before backend import. | Source-tested refusal; no pyglet lifecycle or window presentation claim. |
| `app.backend.pyqt4` | Selector `pyqt4` is explicitly refused before backend import. | Source-tested refusal. No Qt4 binding or application claim. |
| `app.backend.pyqt5` | `_pyqt5.py` selects the shared `_qt.py` Dawn QWidget implementation. | Published strict readback profile is bounded evidence. Native presentation, all event/input variants and every Qt5/runtime combination are broader claims. |
| `app.backend.pyqt6` | `_pyqt6.py` selects the shared `_qt.py` Dawn QWidget implementation. | Same profile distinction as PyQt5; each binding retains its own environment/evidence. |
| `app.backend.pyside` | Selector `pyside` is explicitly refused before backend import. | Source-tested refusal; no original PySide/Qt4 support claim. |
| `app.backend.pyside2` | Selector `pyside2` is explicitly refused before backend import. | Source-tested refusal; its historical oracle tooling does not establish a supported application backend. |
| `app.backend.pyside6` | `_pyside6.py` selects the shared `_qt.py` Dawn QWidget implementation. | Published strict readback profile is bounded evidence; other runtime/presentation combinations remain separate. |
| `app.backend.sdl2` | Selector `sdl2` is explicitly refused before backend import. | Source-tested refusal; no SDL2 event loop or window presentation claim. |
| `app.backend.tkinter` | `_dawn_tk.py`; standalone/supplied-parent raster widgets, native Dawn target and CPU RGB PhotoImage presentation. | Finite Tk criteria remain authoritative. This is not native Vulkan WSI, vsync or transparent-window compositing. Full configuration/input/timer breadth requires its own scoped acceptance. |
| `app.backend.wx` | Selector `wx` is explicitly refused before backend import. | Source-tested refusal; no wx event-loop or window presentation claim. |
| `app.base` | `base.py` defines application/canvas/timer backend interfaces and common event translation. | Abstract methods are extension contracts, not standalone supported backends. Custom subclasses, capability negotiation and all translated events need route/method reconciliation. |
| `app.canvas` | `canvas.py:Canvas`; backend construction, context/current/shared access, size/presentation/events and close. | Selected Tk extent, current/shared resources, close and loss recovery have finite evidence. Context method/value breadth belongs with gloo review; constructor configuration, high-DPI scaling and toolkit event delivery are not universally qualified. |
| `app.create` | `_default_app.py:create()` obtains the default application and calls `Application.create()`. | Source delegation is present. Default-app identity, repeated creation and native-object lifetime require method-level acceptance; instance-based Tk evidence does not automatically prove this module alias. |
| `app.keyevent` | `canvas.py:KeyEvent` preserves key, text, modifier tuple and native provenance. | Source-tested construction/release payloads. Toolkit key mapping, Unicode/composition, focus and physical delivery remain distinct from constructing an event object. |
| `app.mouseevent` | `canvas.py:MouseEvent` stores coordinates/buttons/delta/native provenance and ordered drag history. | Source-tested default values and a two-move drag trail, which excludes the press event. Toolkit coordinates, wheel units, high-DPI mapping and focus cancellation need their own delivered-event evidence. |
| `app.process-events` | `_default_app.py:process_events()` delegates to the selected default application. | Manual instance processing is in the finite Tk scope. Global default selection/reuse and notebook loop restrictions need separate acceptance. |
| `app.quit` | `_default_app.py:quit()` delegates to the selected default application. | Host-preserving Tk instance quit has finite evidence. Global alias behavior, repeated calls and interactions with other applications must be checked separately. |
| `app.run` | `_default_app.py:run()` delegates to `Application.run()`; interactive and gallery paths may return without entering the backend loop. | Source implementation exists. Manual-pump qualification does not prove blocking loops, interactive input hooks or gallery behavior; do not describe this route as missing or fully qualified. |
| `app.timer` | `timer.py:Timer`; interval/iteration state and backend start/stop/timeout events. | Finite Tk one-shot upload/stop is covered. Repeating timers, interval changes, callback restart/stop/error ordering and UI-thread ownership need value-specific evidence. Existing Tk tests identify these cases but are not automatically release admissions. |
| `app.use-app` | `_default_app.py:use_app()` creates/reuses the singleton, rejects a different selected backend and optionally calls backend reuse. | Source implementation exists. Default selection, case/alias handling, reuse callbacks, notebook setup and test isolation remain API-05/06 acceptance work. |

## Additional routes and the next acceptance work

`dawn_headless` is a current core selector absent from the upstream seed. Keep its
existing strict profile evidence and explicitly add its route to API-05; do not
invent a 26th upstream parent. `_test` is an internal pseudo-backend, not a public
shipping backend. The ordinary QWidget route and the Tk raster route are fork
implementations behind familiar public selectors, so they retain documented
presentation and configuration differences.

`canvas.ResizeEvent` and `canvas.DrawEvent` are additional public submodule event
types outside the root-export seed. Their logical/physical size and draw-region
values belong in API-05/06 alongside delivered events; this review does not omit
them merely because they lack separate seed parents.

For each claimed subset, API-06 must bind supported values and ordinary, mutation,
failure and recovery cases to the exact installed wheel/profile. Prioritize default
application aliases, canvas configuration/context lifetime, delivered event values
and timer restart/error ordering. Reuse existing Tk test bodies where they cover
those cases; a source test name alone is not proof that a release admitted it.

This review closes parent identification and source-route disposition for API-01.
It leaves the broader acceptance gaps visible and leaves every original inventory
parent and required pair intact.
