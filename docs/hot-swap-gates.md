# Hot-swap audit gates

The hot-swap profile uses stock PyPI hosts (napari, qtpy, PyQt6 or PySide6, PyOpenGL)
with only `vispy` replaced by `vispy-0.17.0+vulkan.N`. Its claim is narrower than the
strict no-OpenGL profile's:

- vispy and its native module never import, load, resolve or call GL;
- no GL context is created or made current, and no GL draw runs, anywhere in the
  process;
- GL activity by host packages is recorded with attribution, not claimed absent.

A hot-swap result never qualifies a strict row and is never called "no-OpenGL". The
strict audit (`tools/audit_no_opengl.py`, `tools/no_opengl/`) is unchanged.

## Tools

| File | Role |
| --- | --- |
| `tools/audit_hot_swap.py` | Controller: runs a scenario under the observer, scans the renderer package and assesses the gates |
| `tools/hot_swap/probe.py` | Child: runs the scenario script with an attributing audit hook |
| `tools/hot_swap/windows_observer.py` | Debugger-based Windows observer, derived from the strict one |
| `tools/hot_swap/derive_observer.py` | Generates the observer from the strict one |
| `tools/hot_swap/policy.py` | Attribution, correlation of native events, the static scan, and the gates |
| `tools/hot_swap/scenarios/` | The stock napari and Glue baselines and three controls |

`tools/hot_swap/derive_observer.py` generates the observer from the strict observer
`tools/no_opengl/windows.py`, which is pinned and unchanged. A CPU contract test checks
that the committed observer equals that derivation. Each change is an exact replacement
that must match once:

- A GL entry-point lookup is recorded and then single-stepped like any other lookup.
  The strict observer stops there instead; host packages such as PyOpenGL resolve GL
  names at import.
- A GL call records its direct caller. Context, make-current, swap and draw calls still
  stop the process tree, because the gate has failed. Other calls, such as
  `wglGetCurrentContext`, are stepped over. A call whose caller cannot be read is still
  recorded, so a context or draw call fails the gate. Such a call cannot be stepped over,
  so the tree stops.
- A GL library load records its first caller outside the system loader (ntdll,
  KernelBase, kernel32).
- Supporting changes:
  - every event carries wall-clock time;
  - a lookup or call whose step is deferred to another thread is recorded once, when
    its step is taken;
  - an error while handling a GL call stops the tree and is reported;
  - the loader-caller walk shares the strict observer's stack unwinder, which is closed
    with each process;
  - the handle-baseline control source still resolves in `tools/no_opengl/`.

## Gates

| Gate | FAIL | PASS requires |
| --- | --- | --- |
| `renderer_gl` | Any GL import, load, lookup or call attributed to the renderer | All of: complete attribution; complete native API and load coverage; no unattributed GL activity; a successful scenario; and a complete static scan with no GL reference in the renderer's runtime modules |
| `no_gl_context_or_draw` | Any executed context, make-current, swap or draw call under any of its export names, whoever made it | Complete native API coverage and a successful scenario |

Otherwise a gate is `UNVERIFIED`. Overall status is `PASS_HOT_SWAP_GATES` only when
both gates pass. The controller exits 0 for a pass, 1 for any FAIL and 2 otherwise. It
exits 3 on a tool or usage error, and still writes a `TOOL_ERROR` report when it can. An
unreadable child report, for example from a child stopped while writing, removes
coverage instead of failing the scenario.

GL modules, libraries and entry points are recognised by the strict policy
(`tools/no_opengl/policy.py`), reused unchanged. A bare ctypes name such as `opengl32` is
treated as its `.dll`.

Context calls create, bind or present a context in WGL, EGL, GLX or OSMesa. Draw calls
are these families: `glDraw*` (except `glDrawBuffer*`), `glMultiDraw*`, `glClear`,
`glClearBuffer*`, `glClearNamedFramebuffer*`, `glClearTex*`, `glBegin`, `glCallList(s)`,
`glDispatch*`, `glBlit*`, `glEvalMesh*`, `glEvalPoint*`, `glArrayElement` and similar
commands. Some calls are recorded but do not fail the gate:
- queries such as `glGetError`;
- state setters such as `glClearColor` and `glDrawBuffer`.

## Attribution

**Python events** are imports, ctypes library loads and ctypes symbol lookups. Each
takes the *innermost* stack frame that is none of these:
- import machinery, `threading`, `pkgutil` or `lazy_loader`;
- ctypes or the audit tools;
- a GL implementation module (PyOpenGL, the Qt OpenGL bindings);
- a GL binding shim (`qtpy.QtOpenGL*`).

A frame in `vispy.*` means the renderer, and any other module means a host.

**Native events** take their caller first: the direct caller for lookups and calls,
and the loader caller for library loads.
- **Renderer.** Code under the renderer's installed roots is the renderer. The roots
  are the imported `vispy` package directory and a sibling `vispy.libs`, so editable
  and vendored layouts count. Each root is taken both as imported and as resolved
  (junctions, substituted drives, short names), because the observer reports final
  paths. Any path under `site-packages\vispy\` or `site-packages\vispy.libs\` also
  counts as the renderer.
- **Host.** Any other known native module, such as a Qt plugin or a graphics driver,
  is a host.
- **Through Python.** Python's ctypes/FFI (`_ctypes`, `libffi`) and its
  extension-module loader (`python3*.dll`) act for Python code:
  - A GL **call** through them cannot be attributed, because ctypes calls raise no
    audit event. It stays unattributed.
  - A **load or lookup** through them, or with no recorded caller, takes the
    attribution of the Python events that explain it, observed shortly before it:
    a ctypes load request for the same library, or a ctypes lookup of the same
    name.
  - Only Qt's own GL modules and libraries can also be explained by an import of a
    QtOpenGL module.
  - A renderer explanation wins. An unexplained event is unattributed.

**Static scan.** Python raises no import event for a module that is already loaded, and
no lookup event for a cached symbol. So if the host loaded GL first, later renderer use
of it would be invisible to the dynamic record. The controller therefore also scans the
installed renderer package. It looks for:
- imports and `import_module`/`__import__` of GL modules;
- ctypes loads of GL libraries;
- GL libraries in native import tables, and GL entry points imported from any library,
  so a renamed GL library is still found.

References in test modules and `vispy.testing` are listed but do not count, because
they never run in a host process.

## Usage

```
uv run --no-sync --frozen python -I -B tools/audit_hot_swap.py \
    --python <candidate environment python> \
    --script tools/hot_swap/scenarios/stock_napari.py --output <new report path>
```

Use `--no-sync`: a plain `uv run` syncs the project, which can start a native rebuild of
the editable extension.

## Evidence

Run `w3-hot-swap-gates-217` on 2026-10-28 used Windows, CPython 3.12.8 and PyQt6. The
environment was W2's stock lock with only `vispy` replaced by `444402...`. Results are in
`final4/` and `controls-summary-4.json`, which also records the hashes of the tool sources.

| Scenario | Observed |
| --- | --- |
| `control_host_import`: a host module imports PyOpenGL | 16 host GL events, none unattributed; no context or draw. `renderer_gl` is UNVERIFIED because the script never imports vispy, so there is no renderer package to scan. |
| `control_renderer_import`: a `vispy.*` frame imports `OpenGL.GL` | `renderer_gl` FAIL, with 192 renderer events. The two `wglGetProcAddress` calls PyOpenGL makes through libffi are unattributed. |
| `control_gl_context`: Qt creates and binds a GL context | `no_gl_context_or_draw` FAIL on `wglCreateContext`, called by Qt's `qwindows.dll`. `renderer_gl` is UNVERIFIED because the run was stopped. |
| `stock_napari`: image and labels layers, 2D and 3D renders, close | No context or draw. 24 host GL events, 0 renderer and 0 unattributed. The static scan is complete (362 Python files, 3 binaries) and finds one runtime reference: `gloo/glir.py:1591 import OpenGL.GL`. So `renderer_gl` is **UNVERIFIED**. |

Run `w13-glue-hot-swap-224` added `stock_glue`. It runs the five Glue fixture workflows
(scatter, scatter edit, scatter axes, volume, volume edit), each shown and closed, with
stock Glue hosts (glue-core 1.27.0, glue-qt 0.4.2, glue-vispy-viewers 1.4.0, PyQt6
6.11.0). It created no GL context and drew nothing. Its dynamic record has 11 host GL
events (the PyQt6 `QtOpenGL` and `QtOpenGLWidgets` modules and DLLs, and a PyOpenGL
import), with 0 renderer and 0 unattributed. Like napari, `renderer_gl` is UNVERIFIED
only because of the static reference.

Run `w1-w5-native-batch-227` built a local test wheel, `7ad85601...`. It is `444402` with
three changes, all pinned runtime files that ship with the fresh release build (R2):
- W15 removes the static reference below;
- W1 changes `dawn_parser.py`;
- the W5 smooth line end fix.

On that wheel both baselines reach `PASS_HOT_SWAP_GATES`:
- the static scan is complete (362 files, 3 binaries) with no runtime reference;
- `stock_napari` has 24 host GL events and `stock_glue` 11, with 0 renderer and 0
  unattributed;
- neither creates a GL context or draws;
- the three controls keep their verdicts.

The reference sits in `_check_pyopengl_3D()`, part of upstream's legacy OpenGL
`GlirParser`, which the Dawn path never instantiates. `GlirParser` is still a public
class, so a host could reach that path. Removing it is plan item W15. `glir.py` is pinned
by the Tk candidate's runtime inputs, so the fix belongs in the fresh release build (R2).

The baseline's host GL activity comes from two sources:
- napari's PyOpenGL import, which loads `opengl32.dll` and looks up
  `wglGetCurrentContext`;
- qtpy's imports of `PyQt6.QtOpenGL` and `QtOpenGLWidgets`, with their Qt DLLs.

## Limits

- **Windows only.** WSL and Linux rows (W7) need a Linux observer.
- **Immediate callers only.** Native attribution stops at the immediate caller. If the
  renderer reached GL through another native module, the activity would be attributed
  to that module. One example is a graphics driver inside a native swapchain path, if
  W8 selects one. W8 must decide how such activity counts.
- **GL calls through ctypes.** These are never attributed. A run with such calls is at
  best UNVERIFIED.
- **Side-effect imports.** An import made as a side effect of a host module, such as
  qtpy's `QtGui` importing `QtOpenGL`, is attributed to that module, whoever imported
  it.
- **Already-loaded libraries.** Loading a GL DLL that is already loaded produces no
  load event. The static scan and the lookup and call traps cover the renderer's use
  of such libraries.
- **Shutdown.** Python events after the report's last rewrite at interpreter exit are
  not recorded.
- **Private GL implementations.** Statically linked or private GL implementations are
  not covered (`private_or_statically_linked_gl_implementations: false`), as in the
  strict observer.
- **Controls on real data.** The GL-context control exercises only `wglCreateContext`.
  Make-current, swap and draw calls, and the EGL, GLX and OSMesa names, rest on unit
  tests. No scenario reaches `PASS_HOT_SWAP_GATES` on `444402`, because of the static
  reference above (W15).
