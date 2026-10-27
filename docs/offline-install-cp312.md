# Offline CPython 3.12 installation bundle

This guide applies to the older Qt candidate described below. For the newer Tk
milestones, see the [qualified Tk baseline](qualified-tk-baseline.md). Its wheel
identities and profile evidence are separate; the Qt archive is not an installer
for those newer wheels.

This candidate bundle contains the final Windows x86-64 renderer (`62df5e4c…`) and Linux x86-64 renderer (`374a74ea…`), six selected Qt profiles, their original notices, and the Windows core-only TBB runtime. It is a local release candidate; publication and the remaining Windows threedee limitation are separate decisions.

Use an already installed **CPython 3.12.8, 64 bit**, with `venv` and `pip` available. The bundle does not contain Python, Windows components, a Linux distribution, device drivers, or OS package archives. Install those prerequisites before disconnecting the machine. The qualified Linux environment was Ubuntu 24.04 under WSL2 with Lavapipe software Vulkan; native Linux hardware remains unqualified. macOS Metal remains experimental.

The companion source/evidence archive records 13 qualified mandatory rows and the preserved, unqualified Windows threedee attempt. Passing rows use the exact renderer hash and environment receipt recorded in `evidence/no-opengl-matrix.json`. These are scoped functional and native dependency checks, not an OpenGL frame parity or performance guarantee. The Windows threedee attempt timed out in Qt window creation through OLE/RPC; it is not supported by transferring another scenario's receipt.

## Verify and choose one profile

Extract the install archive without flattening directories. `ASSETS.json` records each asset's SHA-256 and size; `SHA256SUMS` records the same content paths. Compare the archive SHA-256 with the separately supplied archive manifest, then verify all extracted file hashes. `DUPLICATE-BASENAMES.json` explains deliberately namespaced files with identical basenames and different contents.

Select exactly one of `windows-pyqt5`, `windows-pyqt6`, `windows-pyside6`, `linux-pyqt5`, `linux-pyqt6`, or `linux-pyside6`. The selected profiles omit unused OpenGL modules and preserve the original third-party licenses. Ordinary `vispy[pyqt6]` and upstream full Qt installations are not this strict profile. Start with a fresh environment; mixing a full Qt installation into it invalidates the selected package inventory.

Windows requires a working Vulkan driver and the OS/runtime DLLs described in the qualification receipt. The tested machine used an NVIDIA RTX 4090. Linux requires the Vulkan loader, a supported Vulkan ICD, X11 for mapped widgets, fonts, and the system libraries in the selected profile's `apt-install-pins.txt`. Those files contain the exact Ubuntu package versions used for qualification; package archives are not bundled. Provision them from an appropriate pinned OS repository or your own offline OS package store. The evidence inventories additionally record the core Vulkan and system package versions. Avoid substituting an arbitrary stock distribution and assuming its installed GL packages pass the no-GL inventory.

After extraction, change into the archive's `install/` directory. All wheel and
requirement paths below are relative to that directory. A Windows PyQt6
installation is:

```powershell
cd install
py -3.12 -m venv C:\vispy-no-gl
C:\vispy-no-gl\Scripts\python.exe -m pip install --no-index --require-hashes --find-links core/windows --find-links profiles/windows-pyqt6 -r core/windows/requirements-core.txt -r profiles/windows-pyqt6/requirements.txt
C:\vispy-no-gl\Scripts\python.exe -c "import vispy; vispy.use(app='pyqt6', gl='gl+'); from vispy import _dawn; print(_dawn.device_info()); _dawn.shutdown()"
```

For PyQt5 or PySide6, replace both profile directory occurrences and select `app='pyqt5'` or `app='pyside6'`. Check `python --version` before installation; the launcher command itself does not enforce the patch version.

The equivalent Linux PyQt6 installation, after OS provisioning, is:

```sh
cd install
/path/to/python3.12 -m venv /path/to/vispy-no-gl
/path/to/vispy-no-gl/bin/python -m pip install --no-index --require-hashes --find-links core/linux --find-links profiles/linux-pyqt6 -r core/linux/requirements-core.txt -r profiles/linux-pyqt6/requirements.txt
/path/to/vispy-no-gl/bin/python -c "import vispy; vispy.use(app='pyqt6', gl='gl+'); from vispy import _dawn; print(_dawn.device_info()); _dawn.shutdown()"
```

Use an available X11 display for widgets. Lavapipe qualification explicitly allowed software adapters; select the intended installed ICD when repeating it. A missing Vulkan ICD must fail with the actual adapter/device error: both final platform artifacts have a preserved native-observed negative control proving no OpenGL fallback. No driver or package changes are part of that test.

The core wheelhouse pins NumPy 2.5.3 and the other dependencies used in the qualified core environments. Scientific host environments used their separate locks, including NumPy 2.4.6. Do not substitute the core dependency pins into a host lock and call it the qualified host environment.

## Hosts and the optional TBB profile

The bundle does **not** contain complete napari, Glue, or threedee dependency wheelhouses. Their actual qualification reports and projected locks/patches are included under `sources/project/compat/host-environments` and `sources/project/compat/host-patches`. Extract the full current implementation source archive to obtain the `tools/prepare_*no_opengl.py` scripts; the projected `sources/project/tools` directory is not a complete source checkout. Prepare the complete locked host wheelhouse separately before an offline host installation. Patched host licenses and provenance must accompany those wheels.

Windows Numba 0.68 hosts require the reviewed CPU TBB runtime to resolve their declared native backend closure. Its small wheel and requirements are included under `tbb/`; install it with `--no-index --require-hashes --find-links tbb -r tbb/windows-numba-tbb-requirements.txt` after preparing the exact host closure. Preserve the original Intel Simplified Software License. This is not an Apache-licensed replacement. Linux host CPU runtime package pins are recorded in the host environment locks and evidence.

## Source and evidence

The implementation is AGPL-3.0-only, with the original BSD license and all third-party notices retained. Individual Qt, PyQt, PySide, SIP, TBB, and other dependency licenses remain their original licenses. Notices are retained inside the wheels and copied under `notices/` in the install archive. The companion archive includes original custom-toolkit source archives, the declared PySide disabled-SSL build-list patch, actual build recipes, source and relocation receipts, selected-profile manifests, package producer source, and the implementation source archive.

The current implementation source archive is Git commit `db157fd75`, including the Linux profile producers, manifests, declared source patch, and corrected compiler contract tests. The original qualification archive at `c781deb92412584d080890b90a07a9a804e6109a` is retained separately; its shipping runtime tree matches Windows source commit `7734055f8bcd16c277f2dcc1c03004fadf452e10`. This guide is separately hashed. Repository: <https://github.com/bipxx/vispy_vulkan>. Build recipes retain the original build paths for provenance and require adapting their owned build roots on a new machine; they are not an interactive installer. Pinned source URLs/hashes, configuration arguments, declared patches, native before/after hashes, original notices, and runtime package versions identify the actual custom inputs. Rebuilding native toolkit sources can depend on the recorded compiler and OS toolchain; the ZIP reproducibility check verifies repeated assembly of these exact frozen assets.

The evidence index rehashes every versioned matrix reference before assembly. Raw qualification, inventory, shutdown, feature-result, capture, and negative-control records accompany those references. Preserved historical failures are explicitly separate from final passing artifacts. Installing the wheels alone does not create a new qualification receipt: use the included audit tools to verify a new environment and its admitted flows.
