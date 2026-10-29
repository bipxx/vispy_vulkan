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
| `tools/hot_swap/loader_audit_linux.c`, `debugger_linux.c`, `linux_observer.py` | Linux observer: LD_AUDIT module, ptrace debugger and runner, derived from the strict ones (see [Linux observer](#linux-observer)) |
| `tools/hot_swap/derive_linux_observer.py` | Generates the Linux observer from the strict one |
| `tools/hot_swap/linux_controls.py` | The Linux observer's native controls |
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
  - If nothing else explains one of Qt's own GL libraries, the nearest Qt binding
    import (PySide6, PyQt6, PyQt5, PySide2) within the preceding second explains
    it. A Qt library dependency loads while its importing module loads. For
    example, qtpy imports `PySide6.QtDataVisualization`, whose library links
    `Qt6OpenGL.dll`. The probe records those binding imports as explanations
    only, never as GL activity.
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

Run `w6-pyside6-hot-swap-230` added PySide6 6.12.0, with stock hosts and `444402`, and
re-ran the PyQt6 scenarios with the final tool:
- **PyQt6** (`gates-pyqt6/`): unchanged. Stock napari has 24 host GL events, 0
  renderer and 0 unattributed.
- **PySide6** (`gates-2/`): every control matches its expected verdict. Stock napari
  creates no GL context or draw. Its dynamic record has 24 host GL events, 0
  renderer and 0 unattributed, which needs the Qt binding rule above: under PySide6,
  qtpy's `QtDataVisualization` import loads `Qt6OpenGL.dll`.
- **PySide6 on the batch test wheel** (`gates-test-wheel/`): both gates pass.

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

## Linux observer

`tools/hot_swap/derive_linux_observer.py` derives the Linux x86-64 observer from the strict
Linux pair in `tools/no_opengl/`, which is pinned and unchanged: the glibc LD_AUDIT module
`loader_audit_linux.c`, the ptrace debugger `debugger_linux.c` and their runner `linux.py`.
As in the strict profile, the auditor alone cannot pass, so a Linux run needs both; without
them it is a `TOOL_ERROR`. A CPU contract test checks that the committed files equal the
derivation. Each change is an exact replacement that must match once:

- **Auditor** (`loader_audit_linux.c`):
  - Every record ends with wall-clock time.
  - A load records the object that requested it, from `la_objsearch`'s `LA_SER_ORIG` call:
    the owner of the `DT_NEEDED` entry, or the object that called `dlopen`. This is the
    Linux counterpart of the Windows loader caller. Objects opened without a search, such as
    the program, the loader and the vDSO, have none.
  - A GL binding, including `dlsym`, records its referencing object, the counterpart of the
    direct caller, and its defining object.
- **Debugger** (`debugger_linux.c`):
  - A GL call records its caller: the module holding the return address at `[rsp]` when the
    export's trap fires.
  - Context, make-current, swap and draw calls are recorded and stop the process tree before
    they execute, under any of the export's names. The C copy of these names is generated
    from the tables in `tools/hot_swap/policy.py`.
  - Other GL calls are recorded and stepped over: `rip` moves past the export's leading
    `endbr64`. The trap stays armed, so no thread is single-stepped. A GL export whose first
    instruction is not `endbr64` fails closed: the call is recorded and an observer error
    stops the tree.
  - A static process's GL lookup is recorded and single-stepped like its other lookups.
  - Every record ends with wall-clock time.
- **Runner** (`linux_observer.py`): parses the new records. A malformed record is an error.
  The coverage rules are unchanged.

Hosts make GL calls that are neither context nor draw calls, so these calls must be stepped
over. For example, the Windows GL-context control recorded 385 host GL events before Qt created
its context (run `w3-hot-swap-gates-217`). Stepping past `endbr64` is equivalent to executing
it only while indirect branch tracking is off for user processes, as in the WSL kernel used
below. The strict observer's breakpoints rely on that too.

**Attribution.** The policy reads POSIX paths too:
- A POSIX `vispy` origin gives POSIX renderer roots.
- The shared `libpython3.x.so` counts as Python's extension-module loader, as does a static
  `python3.x` executable. With a shared libpython, ctypes is built into it.
- `libQt6OpenGL*.so` is one of Qt's own GL libraries.
- The loader caller is the requesting object. So a GL library that another GL library
  requests is attributed to that library's module, a host. For example, glvnd's `libGL.so.1`
  requests `libGLX.so.0` and `libGLdispatch.so.0`. This cannot hide a renderer cause, because
  the requesting library's own load is assessed too.
- A tail call into a GL export names the caller's caller.

**Static scan.** On Linux the scan also covers `vispy.libs`, including versioned `.so` names.
ELF's `DT_NEEDED` names libraries but not the symbols taken from them, so the scan reads GL
entry points from each image's undefined dynamic symbols. An unreadable ELF symbol table makes
the scan incomplete.

**Usage.** Build the collectors with the strict profile's flags, then pass them to the
controller:

```
cc -shared -fPIC -O2 -Wall -Wextra -Werror -o loader_audit.so tools/hot_swap/loader_audit_linux.c
cc -O2 -Wall -Wextra -Werror -o debugger_linux tools/hot_swap/debugger_linux.c
python -I -B tools/audit_hot_swap.py --python <candidate environment python> \
    --script <scenario> --output <new report path> \
    --native-auditor loader_audit.so --native-debugger debugger_linux
```

**Native controls.** `tools/hot_swap/linux_controls.py --output <new directory>` builds the
collectors and synthetic fixtures with the existing C compiler. None of the fixtures is a GL
implementation: a library of GL-named exports named like a GLX vendor library, a host library
that calls them, a driver program and a static program. It verifies the compiled entry bytes,
then checks that:
- a host GL call is recorded with its caller, executed once and stepped over;
- the GL library's load names the host library as its requester, and a `dlsym` lookup names
  the host library as its referencing object;
- a context call, a draw call and a call through an export whose alias is a draw name all
  stop the tree before executing;
- an export without `endbr64` fails closed;
- 32 threads entering a counted export 32 times each are all recorded, and the export ran
  exactly 1024 times;
- a forked child, an exec'd child and a static program are observed the same way.

`tests/contract/test_hot_swap_linux_native.py` runs the controls on Linux only. It also compiles
the collectors without warnings and checks the C context and draw names against the policy.

**Evidence.** Run `w7-linux-observer-251` on 2026-10-29 used WSL Ubuntu 24.04 (kernel 6.18,
glibc 2.39, GCC 13.3):
- The native controls reached `PASS_CONTROLS` on all 20 checks.
- All 3,912 GL-named function exports of WSL's glvnd libraries (`libGL`, `libEGL`, `libGLX`,
  `libGLESv2`) begin with `endbr64`. Mesa's vendor libraries export none.
- The control scenarios ran in an existing environment: CPython 3.12.8 with a shared
  libpython, PyOpenGL 3.1.10 and PyQt6 6.11.0, but no qtpy.
  - `control_host_import`: 26 host GL events, none unattributed, and no context or draw.
    `renderer_gl` is UNVERIFIED because vispy is never imported, as on Windows.
  - `control_renderer_import`: `renderer_gl` FAIL, with 217 renderer events and none
    unattributed. Its 2 host events are glvnd's own dependency loads, described above.
  - `control_gl_context` could not run without qtpy, so both gates are UNVERIFIED.
- A read-only static scan of an installed Linux `vispy-0.17.0+vulkan.1` build was complete:
  361 Python files and 3 ELF images. It found the same `gloo/glir.py:1591` reference as on
  Windows.

## Limits

- **Platforms.** Windows x64 and Linux x86-64. The Linux observer is controlled natively. No
  Linux or WSL scenario row (W7) has run on a candidate yet, and no Linux GL-context scenario
  has run under real Qt.
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
