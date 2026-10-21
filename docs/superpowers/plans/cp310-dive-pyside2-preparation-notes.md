# CPython 3.10 / unchanged DIVE / PySide2 preparation

This is CPU compatibility and environment preparation. No DIVE/PySide2 upstream
graphics fixture, CPython 3.10 native extension, candidate wheel, or graphics
comparison has run in this packet. The four original PyQt5 failures remain in
`tests/reference/dive-opengl`; their source and evidence were not replaced.

The [official PySide2 5.15.2.1 release](https://pypi.org/project/PySide2/5.15.2.1/)
provides a Windows x86-64 wheel tagged for CPython 3.10, with Python `<3.11`.
Its matching shiboken2 wheel and primary hashes are recorded in
`compat/host-environments/dive-pyside2-primary-metadata.json`.
Pinned upstream VisPy has its original `_pyside2.py` backend. Pinned DIVE
selects Qt modules directly through that backend; its source remains unchanged.

The isolated CPython 3.10.16 minimal environment accepted float splitter sizes
`[100.0, 100.5]` on Qt 5.15.2 and supplied `QtWidgets.QAction` and
`QtWidgets.QActionGroup`. This offscreen probe used plain widgets and no VisPy,
OpenGL context, Dawn, or graphics device. The full environment at
`build/host-environments/dive-pyside2-cpython310-upstream` contains 22 exact hashed
wheel packages, including NumPy 1.26.4, pandas 1.5.3 and upstream VisPy 0.17.0.
Three real DIVE imports and its exported QWidget subclass passed; no
QApplication or context was created by that import-only process.

`compat/host-environments/dive-pyside2-environment.json` records the requirements,
source, package digest, module origins, import proof, Qt probe and preserved
PyQt5 failure hashes. DIVE was copied from its verified source package without
inventing distribution metadata. The root `.venv`, shared `uv.lock`, existing
PyQt5 environment, host source pin and admission JSON were unchanged.

The new PySide2 fixture shares the original fixed analytic inputs and exact
landmark assertions. It calls the public DIVE data/edit/screenshot methods.
Its Qt5 `QImage.constBits()` handling passed asymmetric RGBA/ARGB, padded stride,
ownership and null-image CPU checks without a QApplication. The distinct
capture tool refuses a nonempty output directory, records per-child exits and
hashed failure artifacts, and does not modify the old admission JSON. Validation
owns these new fixture/capture/parity files after CPU preparation.

The executed CPU command was:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:QT_API = 'pyside2'
$env:QT_QPA_PLATFORM = 'offscreen'
build/host-environments/dive-pyside2-cpython310-upstream/Scripts/python.exe -m pytest tests/hosts/test_dive_pyside2_parity.py tests/contract/test_package_inputs.py -m 'not gpu' -q
```

Result: **8 passed, 4 GPU tests deselected, exit 0**. Capture CLI `--help` also
ran under CPython 3.10 without rendering. A later upstream capture requires a
root-coordinated hardware slot and removal of the offscreen QPA setting:

```powershell
build/host-environments/dive-pyside2-cpython310-upstream/Scripts/python.exe tools/oracle_dive_pyside2_capture.py --kind upstream --output tests/reference/dive-pyside2-opengl
```

No such capture command ran in this packet. The candidate tests fail when their
independent upstream reference or installed CPython 3.10 candidate is missing;
missing host qualification is not a passing skip.

The existing build markers already select NumPy 2.2.6 on Python 3.10.
[NumPy 2.2.6](https://pypi.org/project/numpy/2.2.6/) declares Python `>=3.10` and
has a CPython 3.10 Windows wheel;
[NumPy 2.4.6](https://pypi.org/project/numpy/2.4.6/) declares Python `>=3.11`.
Primary metadata and wheel hashes are recorded in
`compat/cp310-candidate/numpy-build-compatibility.json`. No marker or shared lock
edit was necessary. The new package-input contract checks that one applicable
NumPy build pin supports each declared CPython 3.10/3.11 target.

`cmake/prepare_cp310_candidate.py --install` created the separate
`build/cp310-candidate/build-env` with ten exact hashed build packages selected
from `uv.lock`: scikit-build-core 0.11.6, nanobind 3.1.0, CMake 4.4.4,
Cython 3.1.5, NumPy 2.2.6 and their locked dependency closure. Preparation records
the interpreter, observed MSVC compiler/hash, toolset, SDK, SOABI and expected
`_dawn.cp310-win_amd64.pyd`, `_sdf_cpu.cp310-win_amd64.pyd` and
`vispy-0.17.0+vulkan.1-cp310-cp310-win_amd64.whl` names.

`compat/cp310-candidate/build-from-stable-snapshot.ps1` passed the PowerShell
parser and was **not executed**. It requires a frozen snapshot whose packaging
hashes match the prepared lock, uses a separate native cache and
`VISPY_INPLACE=OFF`, and checks the protected source CPython 3.12 binary hashes.
Only checksum-verified dependency source trees can currently be reused; CMake
does not import the existing native Dawn libraries into a second build graph.
A fresh dependency compilation and reserved root build slot are still needed.
The NumPy 2.2.6 build versus 1.26.4 runtime SDF/ABI check, external consumer,
rollback and public host graphics qualification remain pending.
