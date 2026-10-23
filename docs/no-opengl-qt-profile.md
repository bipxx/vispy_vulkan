# Selected Qt runtime profiles

The ordinary `vispy[pyqt6]` extra and `uv.lock` select upstream full Qt packages.
They are not the strict runtime profile. Windows CPython 3.12 x64 selected
profiles are available for PyQt6, PyQt5 and PySide6. Each binding and Linux
profile has its own qualification row and cannot inherit another's results.

`compat/qt/windows-pyqt6-no-opengl.json` lists every selected member from the exact
upstream PyQt6 6.11.0 and Qt 6.11.2 wheels. It retains ten binding modules, the
Windows platform plugin, ordinary image/style/network plugins, original notices
and preferred-source URLs/hashes. Native QtGui, qwindows and all other selected
native bytes remain unchanged. Optional QtOpenGL, OpenGL software renderers,
QtQuick/QML and other unselected modules are omitted. The package versions have
the explicit `+vispynogl.1` suffix; PyQt6 depends on that exact selected runtime.
The SIP support wheel is unchanged and hash pinned.

This profile does not disable every OpenGL-capable method inside stock QtGui.
Its admitted Windows path renders with Vulkan offscreen and displays through
QImage/QPainter. Native Win32 Vulkan presentation on the tested NVIDIA driver
loads opengl32 and resolves WGL entry points inside the ICD; a Qt-free control
reproduces that failure. Trimming optional modules cannot fix the driver path.

Reproduce the package bundle from the manifest's hash-verified original wheel
inputs, using the recorded Python 3.12.8 builder and zlib version:

```powershell
$env:PYTHONPATH = 'tools'
python -B -m no_opengl.qt_profile --manifest compat/qt/windows-pyqt6-no-opengl.json --inputs <original-wheel-directory> --output <new-bundle-directory>
```

The tool emits deterministic wheels, a per-member/native-byte/notice provenance
report and `requirements.txt`. Two local rebuilds produced identical wheel
hashes. The checked-in strict requirements contain those exact hashes. Install
the profile into a fresh consumer with its other pinned VisPy/host dependencies:

```text
uv pip install --python <consumer-python> --no-index --find-links <bundle-directory> --require-hashes -r compat/qt/windows-pyqt6-no-opengl-requirements.txt
```

Missing or different artifacts fail installation instead of falling back to
stock Qt. Do not delete DLLs from a running or shared installation. After
installation, run functional/native traces and the exact environment inventory
receipt. A successful package build reports `BUILT_PROFILE_UNQUALIFIED`; it does
not qualify any application or binding by itself. Existing OpenGL reference
environments and original licenses remain separate and unchanged.

The analogous `windows-pyqt5-no-opengl.json` and
`windows-pyside6-no-opengl.json` manifests use the same producer and offline
installation command, substituting their binding name in both paths. They
retain the original pinned PyQt5 5.15.11 / Qt 5.15.2 and PySide6 / Qt 6.12.0
versions respectively. PyQt5 provides nine selected modules because Qt5
combines the SVG widget API in QtSvg. PySide6 provides all ten modules through
Essentials; its selected metadata explicitly omits the Addons, PDF and
WebEngine dependencies, whose modules are outside this QWidget profile.
Shiboken and SIP support wheels remain unchanged. Every original notice from
each selected input wheel is retained, with preferred source URLs and hashes
recorded in the manifest. Repackaging does not replace their original licenses.

Each bundle was rebuilt twice with identical wheel hashes, installed offline
into a fresh environment and checked against every selected installed byte.
All selected modules imported and an actual shown QWidget produced the
expected captured pixel. Repeat this smoke check using the target consumer:

```text
<consumer-python> -I -B tools/no_opengl/qt_profile_smoke.py --binding pyqt5 --manifest compat/qt/windows-pyqt5-no-opengl.json --bundle <bundle-directory> --output <new-report.json>
```

Use `pyside6` for the other profile. `PASS_PROFILE_SMOKE` covers these package
and widget checks; complete VisPy lifecycle, native execution/load observation
and installed dependency receipts remain separate requirements.

The Linux source profile is separate. It targets the recorded Ubuntu 24.04
x86_64 ABI with CPython 3.12; its wheels deliberately make no manylinux claim.
`compat/qt/linux-pyqt6-no-opengl.json` freezes each selected source-built byte,
preferred source archives/build commands, native before/after relocation hashes,
all 127 original notices and the tested 48-package system runtime inventory.
Qt was built with OpenGL/EGL disabled. Ten PyQt modules were rebuilt, then only
their copied RUNPATHs were rebased to `$ORIGIN/Qt6/lib`. Original build artifacts
remain unchanged. Qt SONAME files are regular wheel members; redundant SDK and
full-version aliases are omitted.

This build provides XCB and Vulkan. Wayland, QtNetwork SSL/DTLS, CUPS printing
and the optional X11 AT-SPI bridge are absent; the manifest records those build
choices. Do not infer arbitrary toolkit functionality from a module import.
The package producer verifies the relocated bundle and source receipts:

```text
PYTHONPATH=tools python -B -m no_opengl.qt_linux_profile --manifest compat/qt/linux-pyqt6-no-opengl.json --bundle <portable-bundle> --receipts <source-build-receipt-directory> --inputs <original-SIP-wheel-directory> --output <new-bundle-directory>
```

The resulting bundle includes exact Python package requirements and tested
system package version pins. Install its required system libraries into the
fresh target, then install the wheels using `--no-index --find-links <bundle>
--require-hashes -r compat/qt/linux-pyqt6-no-opengl-requirements.txt`. Missing
artifacts or versions must fail instead of selecting upstream full Qt. The
source-profile producer reports `BUILT_SOURCE_PROFILE_UNQUALIFIED` until the
fresh installed X11/host environment passes its functional and native gates.
