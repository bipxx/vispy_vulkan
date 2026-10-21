# Platform and CI qualification notes

Date: 2026-10-09. This audit records implementation requirements and CI entry
points. The new workflows have not run on GitHub. Linux native rendering,
macOS Metal rendering, the complete wheel matrix, and alternate Qt bindings
remain unqualified. A hosted CPU result cannot admit a graphics platform.

Since this audit, the isolated native surface/library helpers and CMake platform
selection have been implemented. CMake selects Windows/Linux Vulkan or macOS
Metal, enables the required ARC/framework/X11 linkage, and generates the Vulkan
manifest with the platform library suffix. The current Windows extension
compiles and the four shader/texture/state/point CPU contracts pass. Fresh
CPU-only configuration selects Dawn's null backend without a renderer. These
implementation checks do not establish Linux/macOS graphics qualification;
actual native Metal commit instrumentation and the full matrix remain open.

The required target remains Windows 10/11 x86-64 and Linux x86-64 on Vulkan,
macOS 13+ arm64/x86-64 on Metal, standard CPython 3.10–3.14, and separate
PyQt5/PyQt6/PySide6 environments. Linux admission uses X11/xcb, including
XWayland; native Wayland is outside v1.

## Audited baseline blockers and required qualification

| Source before extraction | Required implementation and proof |
| --- | --- |
| `cpp/runtime.cpp` includes `windows.h` unconditionally and stores `HMODULE`. `load_layer()` calls `GetModuleHandleExA`, `GetModuleFileNameA`, `SetEnvironmentVariableA`, `LoadLibraryA`, and `GetProcAddress`. | Extract native library discovery/loading into platform files. Use wide Windows filesystem APIs, `dladdr`/`dlopen`/`dlsym` on Linux, and appropriate bundle/module discovery on macOS. Preserve caller loader settings, report instrumentation-load failure explicitly, and test an installed wheel from a directory outside the checkout without compiler tools. |
| `init_device()` obtains `%SystemRoot%/System32` through `GetSystemDirectoryA` and passes only that directory as Dawn's runtime search path. | Make search-path construction platform specific. Linux must find the configured Vulkan loader/ICD; macOS selects system Metal. Do not load a Vulkan layer on Metal. Capture the actual loader and driver paths/versions in qualification evidence. |
| Adapter enumeration accepts only `BackendType::Vulkan`, reports `Windows backend is not Vulkan`, and writes `info.backend = "Vulkan"`. | Select Vulkan on Windows/Linux and Metal on macOS. Keep hardware and software admission distinct. Query granted device limits and formats from the actual backend; every corpus variant must create its actual render pipeline on both backends. |
| `Canvas` stores `hwnd`/`hinstance`; `ensure_hwnd_surface()` creates `SurfaceSourceWindowsHWND`. `set_surface()` defaults to `GetModuleHandleA(nullptr)`. | Replace the untyped two-integer surface boundary with a tagged native descriptor and platform-specific surface creation. Preserve surface generations, main-thread ownership, zero-size suppression, and recreation after device/handle loss. |
| `_qt.py::_dawn_surface()` always sends `int(winId())` as an HWND. | Dispatch by the actual Qt platform. Supply an X11 window plus a valid Display connection on xcb, and an NSView to an Objective-C++ Metal-layer helper on macOS. Treat WinIdChange, reparenting, screen/DPR changes and close as native-surface lifecycle events. |
| `CMakeLists.txt` forces Vulkan on and Metal off on every OS. | Select only the shipping backend for each OS. Enable Objective-C++ for the macOS helper. Force `TINT_BUILD_SPV_READER=ON`, `DAWN_ENABLE_SPIRV_VALIDATION=ON`, and the `ShaderSourceSPIRV` instance feature on every OS; keep WGSL output, Metal's MSL writer, and Vulkan's SPIR-V writer. Set `DAWN_USE_X11=ON` and `DAWN_USE_WAYLAND=OFF` for Linux v1. |
| `cpp/platform/vk_layer.cpp` uses `__declspec(dllexport)` and a Microsoft linker pragma. Its manifest names `.\\VkLayer_vispy_submit.dll`. | Add a portable export macro and generate the manifest from the built platform library name (`.dll` or `.so`). Retain an absolute, installed-module-relative loader path. Audit dispatch state per Vulkan instance/device instead of assuming one global downstream function table. |
| Submission instrumentation exposes only `vk_queue_submits`. | Add a backend-neutral counter/API identifier while keeping application presents and Dawn submits separate. Metal must count actual native command-buffer commits. The pinned Dawn implementation commits in `src/dawn/native/metal/QueueMTL.mm::SubmitPendingCommandBuffer`; any narrow instrumentation patch must have its own reviewed checksum, keep the upstream source pin identifiable, and preserve callback lifetime. A copied Dawn-submit count does not prove native commits. |
| Some native tests assert Vulkan and BGRA presentation specifically; Qt tests and oracle provenance import PyQt6 directly. | Parameterize backend expectations and selected Qt bindings, use the actual admitted surface format, and retain asymmetric row-origin/alpha comparisons. Required fixtures must fail when their binding, host, hardware, pipeline or reference is missing. |

The pinned schema in `third_party/dawn/src/dawn/dawn.json` defines
`SurfaceSourceXlibWindow` with a `void* display` and a **uint64** window,
`SurfaceSourceXCBWindow` with a connection and uint32 window, and
`SurfaceSourceMetalLayer` with a `void* layer`. Do not truncate an Xlib window,
pass it as an HWND, or pass an NSView where Dawn expects a CAMetalLayer.

## Extraction boundary

The implementation uses `cpp/platform/native_surface.hpp`, `surface_win32.cpp`,
`surface_x11.cpp`, `surface_metal.mm`, `native_library.hpp`, and a
`native_library.cpp` loader with explicit per-OS branches.
Keep `runtime.cpp` as the owner of Dawn instances, surface generations,
submission tickets and completion processing. The platform helpers own only
their native handles and must not retain a dead Python widget.

Use separate bindings such as:

```cpp
set_surface_win32(canvas_id, hwnd, hinstance);
set_surface_x11(canvas_id, display, uint64_t window);
set_surface_metal_view(canvas_id, nsview);
clear_surface(canvas_id);
```

An X11 descriptor states whether its Display is borrowed or owned. A borrowed
connection must outlive its configured surface; an owned connection must be
closed after unconfiguration and relevant submitted work. If Qt's binding
does not expose its native connection, an owned Xlib connection to the same
display server can be opened in the native helper and paired with the Qt
window ID. Validate that strategy on both X11 and xcb through XWayland. Keep
surface operations on the GUI thread and establish Xlib thread rules before
sharing a connection. Zero handles, invalid connections and unsupported Qt
platforms produce contextual errors.

On macOS, QWidget's native view is borrowed. The Objective-C++ helper creates
and retains a CAMetalLayer, attaches it on the main thread, updates its frame
in view points, `contentsScale`, and `drawableSize` in physical pixels, and
passes the layer to `SurfaceSourceMetalLayer`. Store enough attachment state to
detach safely on reparent/close. Release the layer after surface retirement;
do not rely on a widget surviving queued completion. Monitor movement,
fractional scaling, minimize/restore and transparent capture require a real
desktop. Qt stays a Python-selected dependency; this boundary can use native
Cocoa/QuartzCore frameworks without linking the renderer to a Qt wheel.

## Environment and wheel admissions still needed

The project now locks primary Windows napari 0.9.2, PyQt6 6.11.0, and numba
0.68.0. Numba is required for the upstream sparse direct-label fixture.
Build NumPy pins are interpreter specific: 2.2.6 for Python 3.10, 2.4.6 for
3.11, and 2.5.3 for 3.12+. Each isolated consumer must install hashed artifacts
from its selected lock and load the fork only from its installed environment.

The current lock reveals concrete admission gaps:

- PySide6 6.12.0 macOS wheels have a macOS 14 minimum. A macOS 13 PySide6
  environment needs an independently verified compatible pin; a newer desktop
  cannot prove the macOS 13 minimum.
- Numba 0.68.0 and llvmlite 0.50.0 provide no Intel macOS binary wheels in this
  lock. The sparse-label host fixture needs a compatible separate Intel host
  lock or a qualified reproducible native build. Dropping large label values
  would change the requested fixture.
- Napari 0.9.2 requires Python 3.11+, so Python 3.10 core-wheel admission does
  not invent a napari admission there.
- Other host/binding/platform locks are absent. Preserve primary `hosts` for
  the current environment and create isolated qualification locks for napari,
  glue-vispy-viewers 1.4.0, DIVE and selected plugins. Do not mix Qt bindings.
- Visbrain 0.4.5 is conditional: verify and unpack sdist SHA256
  `1b5596e9e6971ffa1ef5450d297955f1d8f3c1d020050b8f4d935e3fa7276ea6`, then run
  its fixture on upstream before candidate rendering admission. Phylib 2.7.1
  remains an import inventory with no GPU workload.

Wheels need clean-machine loader tests, compiled SDF/text/assets/notices,
uninstall/reinstall checks, retained upstream CPU assertions and platform
lifecycle evidence for every supported interpreter cell. Linux/macOS native
dependency audit/repair, Windows DLL discovery, deployment targets, cold-build
time/peak memory, and the 100 MiB compressed-wheel budget remain release gates.
The Cython helper keeps ordinary CPython ABI tags; the wheel must not claim
ABI3. Hosted image updates are recorded, and release compiler/SDK baselines
must be pinned separately from a moving hosted image.

## New CI entry points and their limits

`cpu-contract.yml` builds only the compiled SDF helper and CPU shader contract,
runs original CPU assertions and CPU contracts, and captures hashes/versions
on Windows x86-64, Linux x86-64 and both macOS architectures for pinned patch
versions in the 3.10–3.14 families. Surface support is disabled for those CPU
builds. The optional texture, state and point CPU harnesses should be connected
to CMake/CTest once their integration is coordinated; state descriptors need
`webgpu_dawn` linkage even though the test acquires no device.

`hardware-qualification.yml` explicitly requests dedicated self-hosted Vulkan
Windows/Linux and Metal macOS 13 arm64/x86-64 runners, one binding per cell.
The reusable `native-qualification.yml` installs exact hashed environments,
builds standard CPython wheels, records installed origins and backend/driver
class, and rejects every collected skip or unexecuted case. These definitions
are qualification attempts. Their current platform/binding blockers produce
failure or a queued job when a runner is absent; they do not establish a pass.
Each GPU runner must have its own work folder and exclusive GPU access.
Run it in an interactive desktop session with the actual display available;
headless Windows service sessions and a logged-out macOS machine do not prove
parented presentation or desktop input/DPI behavior.

The separate software-Vulkan cell requires a manifest of the actual pinned
ICD and software OpenGL library hashes in the runner service environment,
captures upstream OpenGL and candidate Vulkan in independent installed
environments, and applies the fixed 2-unit interior, 0.1-percent edge and exact
categorical comparisons. A software adapter does not satisfy hardware gates.

`host-admission.yml` requires per-cell admission records under
`compat/qualifications/<host>/<platform>/<exact-python>/<binding>/admission.json`.
No records are manufactured by these workflows. The record supplies:

- A hashed `requirements_file`, `upstream_vispy_version`, and a successful
  `upstream_fixture_status`.
- `reference_manifest` plus its hash, `upstream_cases`, raw RGBA, filtered GLIR
  and expanded-shader artifacts with verified hashes.
- Candidate `fixture_files` plus their `fixture_sources_sha256` hashes.
- For visbrain, the actual pinned `upstream_sdist` and its hash.
- For phylib, `rendering: false` and `scope: "import-only"` instead of rendering
  fields. Its separate job verifies the installed import/version and has no
  GPU acquisition.

Missing locks, fixtures, references, dependencies or hardware remain unresolved
admissions. Host interpreter cells must be reconciled with actual metadata and
upstream fixture results; only napari's known Python 3.10 incompatibility is
excluded explicitly. This CI skeleton does not replace desktop DPI checks,
the complete scientific matrix or the five alternating performance trials.

GitHub retired the hosted macOS 13 image; the hosted CPU matrix uses current
macOS 15 runners and macOS 13 minimum admission uses explicitly labeled
self-hosted machines. See [GitHub's retirement notice](https://github.blog/changelog/2025-09-19-github-actions-macos-13-runner-image-is-closing-down/)
and [current hosted runner labels](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
Actions are pinned to verified commit SHAs, and uv is pinned to 0.12.5.
The action pins were resolved from their primary GitHub tag APIs; package
hashes come from `uv.lock` and the committed upstream VisPy 0.17.0 PyPI artifact
manifest. GitHub's Node-based actions require an appropriately updated runner.

Local validation: all four YAML files parse and pass checksum-verified
actionlint 1.7.12. The evidence wrapper executed 13 package/SDF cases, rejected
a deliberately skipped required case and rejected an absent glue admission.
Hash-complete upstream-oracle requirement generation also succeeds. These
checks validate the definitions/gates, not any unexecuted platform job.
