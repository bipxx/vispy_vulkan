# Separate Qt consumer environments

The 2026-10-09 preparation created two independent Windows x86-64 CPython
3.12.8 environments. Each contains one Qt binding, pytest 9.1.1, NumPy 2.5.3,
Pillow 12.3.0, PyOpenGL 3.1.10 and the fork's Python runtime dependencies.
The shared `.venv` and host qualification environments were not changed.

| Binding | Local interpreter | Installed Qt stack | CPU preparation |
| --- | --- | --- | --- |
| PyQt5 | `build/qt-environments/pyqt5-cpython312/Scripts/python.exe` | PyQt5 5.15.11, Qt5 5.15.2, sip 12.20.0 | Exit 0; six API checks passed |
| PySide6 | `build/qt-environments/pyside6-cpython312/Scripts/python.exe` | PySide6/Addons/Essentials/Shiboken 6.12.0, PDF/WebEngine 6.12.0.140 | Exit 0; six API checks passed |

`compat/qt-environments/provenance.json` records the exact `uv.lock` input hash,
dependency closure, wheel URLs/hashes, lock hashes, environment paths and probe
hashes. The requirements files permit only wheels compatible with this Windows
CPython 3.12 target; all installs used `--require-hashes --only-binary :all:`.
The installed distribution/version sets match the recorded closure exactly:
15 packages for PyQt5 and 18 for PySide6. No VisPy distribution is installed in
these environments yet.

## Windows Qt5 fallback

The existing universal `uv.lock` pins `PyQt5-Qt5==5.15.19`, but its three recorded
wheels have no Windows artifact. The Python binding itself has a compatible
Windows wheel. For this target only, the consumer lock uses
`PyQt5-Qt5==5.15.2`, whose `win_amd64` wheel hash is
`750b78e4dba6bdf1607febedc08738e318ea09e9b10aea9ff0d73073f11f6962`.
The fallback was checked against primary PyPI release metadata at
`https://pypi.org/pypi/PyQt5-Qt5/5.15.2/json`; its URL/hash and the incompatible
root-lock version are recorded in provenance. The original root lock is
unchanged. A universal CI export using its Qt5 5.15.19 row still needs platform
resolution before a Windows PyQt5 job can install successfully.

Every other selected package version and accepted wheel hash came directly from
the existing lock. PySide6 6.12.0's declared PDF/WebEngine packages are retained
in its dependency closure, even though the CPU probe does not use those modules.

## What the CPU probe checked

`compat/qt-environments/probe.py` imports QtCore, QtGui, QtWidgets, QtTest,
QtOpenGL, NumPy, Pillow, PyOpenGL and pytest. PySide6 also imports QtOpenGLWidgets
and shiboken6. Each module's resolved origin must remain inside the selected
environment. The report preserves origin hashes and installed distribution
RECORD hashes and rejects a second Qt binding.

The probe checks both legacy/scoped enums used for native widgets, input events,
QImage formats and context descriptors. It round-trips a QSurfaceFormat's
version, depth/stencil sizes, sample count, profile, debug option and renderable
type; it inspects the QOpenGLContext API without constructing a context. It also
exercises a QObject signal and weak reference and round-trips NumPy RGBA bytes
through QImage. No QApplication, QWidget, native window, VisPy module, Dawn
device, or OpenGL context is created.

Both bindings expose the legacy and scoped enum paths inspected by the probe.
PySide6's enum/flag values often require `.value` because `int(enum)` raises
TypeError. PyQt5's `QImage.bits()` returns a sip pointer with `setsize`; PySide6
returns a memoryview. Both actual buffer paths passed the RGBA check. These
differences are recorded in `pyqt5.cpu-probe.json` and `pyside6.cpu-probe.json`.

Reproduce preparation in fresh directories:

```powershell
uv venv build/qt-environments/pyqt5-reproduce-1 --python 3.12.8
uv pip install --python build/qt-environments/pyqt5-reproduce-1/Scripts/python.exe --require-hashes --only-binary :all: -r compat/qt-environments/pyqt5-windows-cpython312.txt
build/qt-environments/pyqt5-reproduce-1/Scripts/python.exe compat/qt-environments/probe.py --binding pyqt5 --output build/qt-environments/pyqt5-reproduce-1.cpu-probe.json

uv venv build/qt-environments/pyside6-reproduce-1 --python 3.12.8
uv pip install --python build/qt-environments/pyside6-reproduce-1/Scripts/python.exe --require-hashes --only-binary :all: -r compat/qt-environments/pyside6-windows-cpython312.txt
build/qt-environments/pyside6-reproduce-1/Scripts/python.exe compat/qt-environments/probe.py --binding pyside6 --output build/qt-environments/pyside6-reproduce-1.cpu-probe.json
```

Use each environment's Python executable directly. `uv run` from the project
directory can resolve the project environment and defeats this isolation.

## Native graphics gates remain open

The current local native module is a CPython 3.12 Windows x86-64 `.pyd`. These
environments can later consume a qualified wheel, installed with its recorded
artifact SHA-256 and `--no-deps`, or the current fork source through an explicit
`PYTHONPATH=<workspace>/src`. For a source run, set `QT_API` to the selected
binding, disable pytest plugin autoload, and assert `vispy.__file__` points to
that `src/vispy` directory before constructing a canvas. Record the resolved
`vispy._dawn` origin, its hash and the Vulkan layer manifest/library hashes for
the exact build under test. Source imports do not constitute wheel qualification.

After the native build is stable and the root agent reserves the GPU, the public
Qt lifecycle suite must run independently in both environments, covering parent
widgets, child overlays, physical-size/DPI changes, framebuffer screenshots,
device loss/recovery, native-handle retirement and clean process exit. No such
GPU test was run in this preparation packet. Rendering, presenting, host
integration, wheel consumption, other interpreters, and Linux/macOS remain
unqualified by this CPU evidence.
