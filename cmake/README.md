The supplied source trees are pinned in `dependencies.lock.json`. CMake does
not download Dawn dependencies or follow branches. The configure step checks
the vendored tree checksums; run the same check independently with:

```powershell
.venv/Scripts/python.exe cmake/verify_dependencies.py
```

GitHub source archives expand the vendored VisPy `.git_archival.txt` placeholders.
CMake restores recognized archive expansions to their original pinned bytes before
checking dependencies. To prepare a downloaded archive before a direct checksum
check or source-distribution build, run:

```console
python cmake/verify_dependencies.py --restore-archive-metadata
```

The default standalone checker remains read-only. Git checkouts and unrecognized
metadata edits are not rewritten; every dependency still has to match the existing
lock byte for byte. Explicit immutable-origin builds retain their separate checks.

For a fresh Windows qualification environment, synchronize the lock with the
primary host and build tools, then use the Visual Studio x64 preset:

```powershell
uv sync --locked --python 3.12.8 --extra pyqt6 --group dev --group build --group hosts
.venv/Scripts/cmake.exe --preset windows-release
.venv/Scripts/cmake.exe --build --preset windows-release
```

The existing development environment may contain other host/plugin packages.
Use `uv sync --inexact` when preserving those packages; do not clear another
worker's environment. `hosts` selects napari 0.9.2 and PyQt6 6.11.0. Run PyQt5
and PySide6 admission in separate environments using their corresponding
extras. No alternate host is admitted by an import alone.

The `pyqt5` extra pins its Qt runtime by platform: Windows uses
`PyQt5-Qt5==5.15.2`, which provides Windows wheels, while Linux/macOS retain
`5.15.19`. The newer runtime has no Windows wheel. Export the project lock for
the selected binding rather than combining Qt bindings in one environment.

PEP 517 builds pin CMake, nanobind, Cython, and build NumPy. The compiled CPU
SDF helper comes directly from the unchanged upstream `.pyx` file and includes
the selected NumPy headers. Generated C and normal build outputs live under
`build/`. Editable installs use scikit-build-core's redirect mode. The explicit
`VISPY_INPLACE=ON` developer preset also copies the built extensions into `src`
for an existing direct-source import workflow.

Optional CPU shader, texture, state, and point contracts can be enabled with
`-DVISPY_BUILD_CONTRACT_TESTS=ON`; build `shader_contract`, `texture_contract`,
`state_contract`, and `point_contract`, then invoke
`ctest --test-dir <build-directory> -C Release --output-on-failure`.
The same option also builds `native_contract` (native module paths, symbols,
loader environment and Windows hidden-window lifetime) and `vk_layer_contract`
(mocked multiple Vulkan instances/devices/queues and retirement), plus a small
shared-library fixture. No Vulkan loader or GPU is used by these tests.
Hosted CPU jobs also set `-DVISPY_CPU_CONTRACTS_ONLY=ON`: Dawn uses its null
backend, and native renderer and installed-layer targets are omitted. The
platform contract checks loader operations on every OS and hidden Win32 handles
on Windows; it does not acquire Linux X11 or macOS Metal surfaces in null mode.
This mode cannot produce a renderer wheel. C++ descriptor contracts do not
create a device.

Wheel validation uses an already-built wheel, then creates a unique consumer
environment in the system temporary directory. It exports locked runtime
dependencies, requires wheel SHA256 hashes, imports using isolated Python,
exercises the renderer, compiled SDF, text and assets, and verifies uninstall
and upstream reinstall:

```powershell
uv build --wheel --out-dir dist
.venv/Scripts/python.exe -m pytest tests/contract/test_installation.py -q -m wheel
```

Set `VISPY_TEST_WHEEL` to the absolute wheel path when multiple wheel artifacts
are present. The test never builds the shared native targets or clears an
existing reference environment. Native and font notices are installed under
`vispy/_licenses` and as distribution license files.

Native presets are `windows-release`, `linux-release`, and `macos-release`;
`unix-release` remains an alias for Linux. Windows/Linux use Vulkan; Linux
requires X11 development libraries and a native X11 surface. macOS selects
Metal, Objective-C++ ARC, and Cocoa/QuartzCore/Metal frameworks, with a default
macOS 13 deployment target. Native Wayland is not an admitted surface. The
Vulkan layer manifest is generated with the actual platform library suffix;
Metal packages do not load a Vulkan layer. Linux/macOS rendering still requires
qualification on the designated systems.

The [Linux software-Vulkan workflow](../.github/workflows/linux-vulkan.yml)
builds a real CPython 3.12 renderer wheel on Ubuntu, checks package/license bytes
and controlled stripped native origins, then installs it outside the checkout.
Its lavapipe consumer checks renderbuffer allocation/resize ownership, clear,
fractional smooth lines/reuse, compiled text and million-marker rendering.
Adapter details, ICD descriptor/hash, system package versions, raw frames,
counters and logs are retained. The job fails on a missing software adapter or
failed rendering check; it grants no native GPU or manylinux qualification.
WSLg X11/Qt checks remain separate local validation.

The [Metal wheel build workflow](../.github/workflows/metal-wheel.yml) provides
separate hosted macOS arm64 and Intel CPython 3.12 jobs for the native renderer.
It checks the macOS 13 wheel tag, Mach-O architecture, controlled stripped native
origins, system-library dependencies, source package bytes, license copies and
the 100-MiB compressed-wheel budget. A fresh external consumer imports both
compiled extensions and compares the CPU SDF helper with the retained upstream
arrays. These jobs provide build/package evidence; graphics qualification still
requires actual Metal rendering and lifecycle results.

For a stable milestone while other agents continue source edits, run
`python cmake/snapshot_wheel_sources.py <new-snapshot-directory>` and build that
snapshot with a separate CMake cache and `VISPY_INPLACE=OFF`. The tool copies
project inputs and records their SHA256s, excludes native products, and links
immutable dependency trees. Verify dependency checksums before and after the
build. Preserve the snapshot and resulting wheel hash with consumer evidence.
