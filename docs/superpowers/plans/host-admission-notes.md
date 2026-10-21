# Pinned host inventory and admission status

The 2026-10-09 inventory fetched the exact recorded source pins, scanned their
Python imports, and imported the recorded modules in four separate Windows
x86-64 environments. All four final import probes exited 0. These are CPU
import proofs. No DIVE, napari-threedee, or visbrain upstream rendering fixture
or candidate comparison was run in this packet.

`compat/hosts.lock.toml` retains the original commits, tag objects and release
hashes. It now records archive URLs/hashes, complete source-tree hashes, actual
dependency declarations, package hashes, probe module names, and hashes of the
checked-in evidence under `compat/host-environments/`. The inventory algorithm
hashes each sorted relative filename, a NUL byte, and its file bytes. Generated
bytecode and Git metadata are excluded. Every source file also has an individual
size and SHA-256 in its source inventory. Extraction rejects traversal, absolute
paths, links and hash mismatches before writing any source member.

| Host | Exact inspected source | Files | Isolated import environment | Probe result |
| --- | --- | ---: | --- | --- |
| DIVE | `Dive576/DIVE`, `aa575e1c020f0c5e8227bfb234fa192fa2b12924` | 60 | CPython 3.11.11, PyQt5 5.15.11, NumPy 1.26.4, pandas 1.5.3, upstream VisPy 0.17.0 | 3 modules passed |
| napari-threedee | `napari-threedee/napari-threedee`, `7bd485085186ebe1907f8de931aa7a93e0d58a83` | 174 | CPython 3.12.8, PyQt6 6.11.0, napari 0.9.2, NumPy 2.5.3, upstream VisPy 0.17.0 | 3 modules passed |
| visbrain | PyPI 0.4.5 sdist, SHA-256 `1b5596e9e6971ffa1ef5450d297955f1d8f3c1d020050b8f4d935e3fa7276ea6` | 148 | CPython 3.11.11, PyQt5 5.15.11, NumPy 1.26.4, setuptools 80.9.0, upstream VisPy 0.17.0 | 3 modules passed after recording an undeclared dependency failure |
| phylib | `cortex-lab/phylib`, `457915ba7ef9063504484769d775b3bb1ccfd74a` | 60 | CPython 3.12.8, NumPy 2.5.3; neither VisPy nor Qt installed | 12 modules passed; no VisPy or Qt imports |

The archive hashes are respectively
`28300472a4cc2d77e4f13820c7cc26369a6ae3148c0ebcba6cc03bb7b3fd7659`,
`4ec3034db322ae8b4de34de2a30f6258a0a0ea8bec0b0b57ecd0db6e8cfb993e`,
the visbrain sdist hash above, and
`f57a049cc44d0c3b610dcc0cb4bd25ad5bac8fa76d7553611502c72b8afa88e9`.
The DIVE repository was resolved through GitHub's exact-commit search and the
matching repository archive; the similarly named unrelated projects are not
used. The original download records and raw probe paths remain under
`build/host-sources/`. Checked-in probe paths use `$ENV` for the selected isolated
environment. Reports include interpreter/platform, installed distributions,
wheel RECORD hashes, module origin hashes and the inventory tool hash.

## DIVE public fixture feasibility

`DIVE/__init__.py` exports `DIVEWidget` from `DIVE/_widget.py`. The source has no
`pyproject.toml`, `setup.py`, `setup.cfg` or requirements file. Its README declares
pandas and VisPy, with OpenCV, pint and qdarkstyle optional. Actual package imports
also require NumPy, pytz and the Qt binding selected by
`vispy.app.use_app().backend_name`. The widget and manager dynamically import
that binding's `QtCore`, `QtGui` and `QtWidgets` modules.

The package imports top-level VisPy in `_widget.py`, `_components/dive_manager.py`,
`_components/dive_table_row.py`, `_gui/configure_widgets.py`, `_gui/custom_qt.py`,
`_gui/dialogs.py`, `_plotting/artists.py`, `_plotting/axis_instance.py`,
`_plotting/custom_vispy.py`, and `_utilities/validators.py`. It uses `vispy.app`,
`color`, `geometry`, `io`, `scene`, `util` and `visuals`. The custom canvas inherits
`SceneCanvas`, its two cameras inherit `PanZoomCamera` and `TurntableCamera`, and
it creates real Text and Line visuals. The complete module/name/line inventory,
including dynamic Qt imports, is checked in.

The public scatter fixture can construct a `DIVEWidget`, add a pandas DataFrame
through `add_data`, create a `2d` axis through `add_axis`, add a scatter artist,
call `display_axis`, show the widget, and wait for settled Qt paint events.
`take_screenshot(file_path)` is also public. Its manager's `grab_picture` combines
`QWidget.grab()` with `canvas.native.grabFramebuffer()` through QPainter. It
catches screenshot errors internally, so a qualification harness must verify
that a new image was actually written and contains plotted landmarks. A second
image after public `edit_data` must verify the changed data reached the display.

`tools/oracle_dive_admission.json` contains those steps, critical source hashes,
and the pending upstream/candidate states. Both `successful_fixtures` and
`reference_manifest` remain empty. CPU import success cannot admit a screenshot.

The isolated Qt5 environment follows actual source constraints: the manager uses
`qtwidgets.QAction` at line 87 and Qt5 enum names, and ArrowArtist calls
`pandas.DataFrame.append` at `_plotting/artists.py:213`. The Python 3.11 lock uses
pandas 1.5.3 with NumPy 1.26.4 to retain that method. Qt6 and pandas 2/3 cells have
not been qualified. Optional theme/unit/video features are outside this probe.

The prepared local interpreter is
`build/host-environments/dive-cpython311-pyqt5/Scripts/python.exe`. The next step
requires an actual upstream Qt5 screenshot capture, then the same public fixture
against a compatible candidate wheel, with pixel/landmark checks and clean exit.

## phylib actual import inventory

The pinned `requirements.txt`, read by setup.py, declares NumPy, SciPy, dask,
requests, responses, tqdm, toolz, joblib and mtscomp. Its package has no static
VisPy import. The only package Qt import is function-scoped
`from PyQt5.QtCore import QByteArray` in
`phylib/utils/_misc.py:101`, inside `_decode_qbytearray`; its test file contains a
separate Qt import. The Qt serialization function was not called by this probe.

The imported modules were `phylib`, `phylib.utils`, `phylib.utils._misc`,
`phylib.utils.geometry`, `phylib.io`, `phylib.io.model`, `phylib.io.traces`,
`phylib.stats`, `phylib.stats.ccg`, `phylib.stats.clusters`, `phylib.electrode`,
and `phylib.electrode.mea`. The root reported version 2.7.1. The process loaded
zero VisPy modules and zero Qt modules. This evidence concerns phylib's data
library, and does not qualify the separate phy GUI renderer or every CPU method.

## Plugin and conditional visbrain evidence

napari-threedee declares its runtime dependencies in `pyproject.toml`, including
napari >=0.5.0, VisPy, libigl, morphosamplers and zarr <3. Its manipulator visual
imports `Line`, `Compound` and `Markers` from `vispy.scene`. Other package VisPy
imports occur in `napari_manipulator_backend.py`, `data_models/spheres.py` and
`manipulators/manipulator_utils.py`. The root and both recorded manipulator
modules imported successfully with the full declared dependency set. Pydantic
reported the pinned source's obsolete `allow_mutation` configuration key.

The source-only archive does not contain the hatch-vcs generated `_version.py`,
so unchanged source imports report `__version__ = "unknown"`. This inventory
copies the verified package unchanged and does not invent a version or install
fake entry-point metadata. A packaging proof must use the real pinned VCS source
and validate its `napari.manifest` entry point, followed by a public plugin
interaction/rendering fixture. Source imports alone do not prove registration.

The first wheel-only dependency resolution failed because zarr 2 depends on
asciitree, which has no usable wheel. The final immutable lock permits only that
hashed `asciitree==0.3.3` source archive. A separate hashed build-tool lock installs
setuptools 80.9.0 and wheel 0.45.1 before installation with build isolation
disabled. The environment was created successfully; its installed asciitree
RECORD hash is preserved. No unmanaged build dependencies were downloaded.

visbrain 0.4.5's declared requirements are NumPy >=1.13, SciPy, VisPy >=0.5.3,
matplotlib >=1.5.5, PyQt5, Pillow and PyOpenGL. Its config module imports PyQt5
directly and creates a QApplication. It imports top-level VisPy across its object,
custom visual, camera, GUI and IO modules; all exact paths are in the source
inventory. The first object/visual import failed at `visbrain/io/path.py:4` because
`pkg_resources` was undeclared. That failure is preserved in
`visbrain.import-failure-1.json`. Adding hashed setuptools 80.9.0, which supplies
the required module, made the three recorded imports pass. The source was not
patched. Rendering remains conditional on a successful unmodified upstream
fixture, including any assets needed by that fixture.

## Reproduction and remaining gates

Do not synchronize a shared environment. The `.in` files describe dependency
environments; the host code is the separate immutable source pin. Resolve a lock
using uv 0.12.5, the recorded Python minor/platform, `--generate-hashes` and
`--exclude-newer 2026-10-09T23:59:59Z`. Existing `.txt` files already contain exact
versions and accepted artifact hashes. DIVE, visbrain and phylib installation
uses `--require-hashes --only-binary :all:`. The plugin additionally uses
`--no-build-isolation --no-binary asciitree` after installing its build-tool lock.

For example, prepare a fresh DIVE source/environment in PowerShell:

```powershell
$source = & .venv/Scripts/python.exe tools/host_inventory.py fetch --host dive --directory build/host-sources/reproduce-1
if ($LASTEXITCODE -ne 0) { throw 'Pinned source fetch failed' }
uv venv build/host-environments/dive-reproduce-1 --python 3.11.11
uv pip install --python build/host-environments/dive-reproduce-1/Scripts/python.exe --require-hashes --only-binary :all: -r compat/host-environments/dive-windows-cpython311-pyqt5.txt
```

Verify the complete source-tree digest with `host_inventory.py scan --host dive
--source $source --output build/host-sources/reproduce-1.inventory.json`. Copy
only the verified `DIVE` package into the new environment's `Lib/site-packages`
without modifying its files or synthesizing distribution metadata. The import
probe verifies the installed package digest again:

```powershell
build/host-environments/dive-reproduce-1/Scripts/python.exe tools/host_inventory.py probe --host dive --output build/host-sources/reproduce-1.imports.json
```

Equivalent locks exist for phylib, visbrain and the plugin. Each probe executes
outside the checkout, checks package origins remain in the selected environment,
preserves import errors and returns nonzero for failure. The source/archive
fetcher refuses to replace existing source directories.

The CPU contract command is `python -m pytest tests/contract/test_host_inventory.py
-q`. The remaining gates are DIVE public rendering and edit screenshots,
napari-threedee packaging/registration and real plugin interaction, and a
successful upstream visbrain fixture before conditional admission. None of these
new environments qualifies another interpreter, Qt binding, OS or GPU. Missing
source, failed imports, absent screenshots and nonzero exits are failures, never
passing skips.
