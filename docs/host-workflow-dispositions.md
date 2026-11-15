# Downstream scientific host workflow dispositions (`HOST-01..06`)

This document records the current-wheel (`vispy 0.17.0+vulkan.2`) dispositions,
claim-separation rules, and verification boundaries for downstream scientific
hosts (`HOST-01` through `HOST-06`, plus `SCI-05` / `H03`). Machine-readable
current-wheel renewal receipts are recorded in
`compat/api-acceptance/host01-06-current-wheels-v1.json` and contract-checked by
`tests/hosts/test_current_wheel_host_renewal.py`.

## 1. Strict separation of host profiles (`HOST-01` vs `HOST-02` / `HOST-03`)

VisPy-Vulkan evaluates downstream scientific hosts under two strictly separated
profiles that MUST NOT be conflated:

| Dimension | Stock Hot-Swap Profile (`HOST-01`, `HOST-02` hot-swap) | Patched Strict No-OpenGL Profile (`HOST-02` strict, `HOST-03`) |
| --- | --- | --- |
| Host packages | Unmodified upstream releases (`napari==0.10.0`, `QtPy==2.4.3`, `glue-core==1.27.0`, `glue-qt==0.4.2`, `glue-vispy-viewers==1.4.0`, `napari-threedee==0.0.29`, stock `PyQt6`/`PySide6`, `PyOpenGL==3.1.10`) with **only** `vispy` replaced | Explicit recorded no-OpenGL host patches (`compat/host-changes.json`, `compat/host-patches/*.patch`) plus GL-free Qt6 build (`PyQt6==6.11.0+vispynogl.1`, `PyQt6-Qt6==6.11.2+vispynogl.1`); `PyOpenGL` absent |
| Audit controller | `tools/audit_hot_swap.py` (`docs/hot-swap-gates.md`) | `tools/audit_no_opengl.py` + `tools/no_opengl_host_probe.py` |
| Passing verdict | `PASS_HOT_SWAP_GATES` (`renderer_gl == PASS`, `no_gl_context_or_draw == PASS`) | `PASS_ALL_NO_OPENGL_GATES` (`no_gl_execution == PASS`, `no_gl_loads == PASS`, `no_gl_install_link_requirement == PASS`) |
| Host GL imports / loads | Allowed when attributed solely to `host` (`0` `renderer` GL events, `0` `unattributed` GL events, `0` GL contexts or draw calls) | Forbidden anywhere in candidate runtime, load trace, or declared package/binary closure |
| Matrix / claim boundary | Scoped strictly to `hot-swap profile only; never a strict no-OpenGL qualification` | Optional (`mandatory: false`) rows in `compat/no-opengl-matrix.json` and `compat/no-opengl-napari-0.10.0.json` stay pinned to their recorded `0.17.0+vulkan.1` artifacts (`62df5e4c...` Windows, `374a74ea...` Linux) unless an explicit optional-row matrix renewal is performed; current-wheel `0.17.0+vulkan.2` runs (`9919a280a5de2c4bec45837078cb1d405e7169933ddcfb0758aa7d6a82722d39` Windows, `e600b29e5259b896cc9d0fe36bbb5760260946aef53c013f8fc74e2fd0153007` Linux) are detached current-wheel renewal receipts (`artifact_admitted_to_no_opengl_matrix: false`) |

## 2. Per-host dispositions (`HOST-01..06`)

| ID | Host(s) | Version / Pin | Current-Wheel (`0.17.0+vulkan.2`) Disposition | Scope & Non-Overclaim Boundary |
| --- | --- | --- | --- | --- |
| `HOST-01` | Stock `napari` & stock `Glue` hot-swap | `napari==0.10.0` (`df9de6c9...`), `QtPy==2.4.3` (`72095afe...`), `glue-core==1.27.0`, `glue-qt==0.4.2`, `glue-vispy-viewers==1.4.0` | Renewed on current Windows (`9919a280...`, `gap-w2-6-windows-978`) and WSL (`e600b29e...`, `gap-w2-6-wsl-979`) wheels under `tools/audit_hot_swap.py` (`PASS_HOT_SWAP_GATES`) | Proves zero renderer GL imports/loads/calls and zero GL context/draw creation when replacing only `vispy` in stock hosts; never claims absence of host `PyOpenGL` / `QtOpenGL` imports |
| `HOST-02` | `napari` (`>= 0.10.0`) | `napari==0.10.0` (`2fb099d8...` sdist; stock `df9de6c9...` vs patched `fa9d6917...`), `npe2==0.10.0` | Both stock hot-swap (`PASS_HOT_SWAP_GATES`) and patched strict no-OpenGL (`PASS_ALL_NO_OPENGL_GATES`) renewed on `0.17.0+vulkan.2` (`978`, `979`); `napari 0.9.2` remains retired (`NAPARI_VERSIONS = ('0.10.0',)`) | Covers 2D image, sparse `int64` labels (`numba==0.68.0`), overlay visibility, 3D volume, Dawn `lose_device()` recovery, PNG export, clean close, and 10 zero shutdown gauges |
| `HOST-03` | Optional strict host rows (`napari`, `napari-threedee`, `Glue`) | `compat/host-changes.json` (`napari 0.10.0`, `qtpy 2.4.3`, `glue-qt 0.4.2`, `glue-vispy-viewers 1.4.0`, `napari-threedee 0.0.29` `de115619...`) | Detached current-wheel strict no-OpenGL renewal receipts recorded on `9919a280...` (Windows `978`) and `e600b29e...` (WSL `979`, owned `Xvfb` + Mesa `9c5c41b3...`); `compat/no-opengl-matrix.json` and `compat/no-opengl-napari-0.10.0.json` remain unmodified | Detached candidate/current-wheel strict verification (`artifact_admitted_to_no_opengl_matrix: false`, `matrix_modified: false`); historical `R1` (`windows-vulkan-napari-threedee-pyqt6` `r1: "open"`) stays open pending intermittent OLE startup-stall root-cause proof |
| `HOST-04` | `DIVE` | Commit `aa575e1c020f0c5e8227bfb234fa192fa2b12924` (`v1.0.2`) | **`NOT_ADMITTED` — PySide2-legacy excluded unless ported to PyQt6/PySide6** | Pinned DIVE imports `PySide2` directly (`qtpy_used: false`) and accesses `QtWidgets.QAction` / `QActionGroup` removed in Qt6 (`compat/host-environments/dive-pyside6-investigation.json`); legacy `PySide2` / CPython 3.10 is outside supported Qt6 bindings, and historical upstream `ArrowVisual` (`arrow_type`) failure remains unwaived |
| `HOST-05` | `napari-threedee` | `0.0.29` (`de115619...` wheel / `7bd48508...` source), `asciitree==0.3.3` (`d3c865c2...`) | Renewed on `0.17.0+vulkan.2` (`978`, `979`) for rendered 3D manipulator activation, handle picking, settled synthetic `QTest` drag translation (`translation[2] > 0.25`), volume update, `lose_device()` recovery, callback retirement, and clean close | Finite plugin manipulator workflow on `napari 0.10.0` + `PyQt6`; does not close `R1` (`docs/threedee-startup-diagnosis.md`) or claim arbitrary third-party napari plugin parity |
| `HOST-06` | `Glue` (`+ H03`), `phylib`, `Visbrain` | `glue-vispy-viewers==1.4.0`, `phylib==2.7.1` (`457915ba...`), `visbrain==0.4.5` (`1b5596e9...`) | **Split by actual capability**: `Glue` rendered 5-workflow + `H03` invalidation-before-update renewed on `0.17.0+vulkan.2`; `phylib` renewed as **import-only CPU capability** (`rendering_qualified: false`) co-resident with `0.17.0+vulkan.2`; `Visbrain` kept **`NOT_ADMITTED`** as a strict/Qt6 host, with historical `cp311/PyQt5` import-only inventory strictly separated from `cp312` VisPy-primitive rendered smoke | Never promotes `phylib` or `Visbrain` import inventories to rendered GUI host qualification |

## 3. Detailed host notes and historical reconciliations

### 3.1 `Glue` 5-workflow renewal and `H03` (`SCI-05`) FRB cache-invalidation reconciliation

- **Preserved historical failure**: `tests/reference/glue-opengl/manifest.json`
  retains the original `H03` `volume_edit` observation where mutating `Data`
  components directly without invalidating `glue-vispy-viewers`'s
  `FixedResolutionBuffer` (FRB) cache returned unchanged volume bounds/voxels on
  both upstream OpenGL VisPy and VisPy-Vulkan.
- **Reconciled upstream host protocol**: As bound in
  `compat/api-acceptance/h03-upstream-disposition-v1.json`
  (`PASS_H03_HISTORICAL_UPSTREAM_DISPOSITION_ONLY`, corrected Glue FRB
  invalidation-before-update protocol)
  and implemented in `tools/fixture_glue_extensions.py` (`invalidate_cache`),
  upstream `glue-vispy-viewers` caches 3D volume FRB arrays by `Data` reference
  and requires invalidating the viewer's layer-state cache before calling
  `data.update_components(...)`.
- **Current-wheel verification (`978` Windows & `979` WSL)**:
  1. Strict no-OpenGL `glue` probe (`tools/no_opengl_host_probe.py --scenario glue`)
     passes `PASS_ALL_NO_OPENGL_GATES` on `9919a280...` and `e600b29e...`.
  2. Stock hot-swap `tools/hot_swap/scenarios/stock_glue.py` passes
     `PASS_HOT_SWAP_GATES` across all five workflows (`scatter`, `scatter_edit`,
     `scatter_axes`, `volume`, `volume_edit`).
  3. Direct `H03` `cache_control` verification on `0.17.0+vulkan.2` proves both
     that omitting `invalidate_cache(data)` reproduces the stale FRB array and
     that calling `invalidate_cache(data)` prior to `data.update_components(...)`
     yields a distinct, non-blank updated RGBA volume frame with clean shutdown
     (`10/10` zero live gauges).

### 3.2 `DIVE` (`HOST-04`) PySide2-legacy exclusion

- `compat/no-opengl-matrix.json` (`id: "dive-admission"`) records `DIVE` as
  `NOT_ADMITTED`.
- `compat/host-environments/dive-pyside6-investigation.json` proves that pinned
  `DIVE` (`aa575e1c020f0c5e8227bfb234fa192fa2b12924`) imports `PySide2` directly
  without `qtpy` and fails on Qt6 / `PySide6` (`6.12.0`) with
  `AttributeError: module 'PySide6.QtWidgets' has no attribute 'QAction'`.
- `PySide2` (`5.15.2.1`, CPython 3.10) is a legacy EoL Qt5 binding outside the
  supported CPython 3.12+ / Qt6 (`PyQt6`, `PySide6`) target profile. In addition,
  `compat/host-environments/dive-pyside2-candidate-w10-scoped-parity.json` and
  `tests/hosts/test_dive_parity.py` preserve the upstream OpenGL baseline
  `ArrowVisual` (`arrow_type`) failure (`arrow` workflow). `DIVE` remains
  excluded unless ported upstream to `PyQt6` / `PySide6` (or Qt6-clean `qtpy`)
  and re-qualified through an explicit host admission run.

### 3.3 `phylib` (`HOST-06`) import-only CPU capability vs rendered GUI hosts

- `phylib` (`2.7.1`, commit `457915ba7ef9063504484769d775b3bb1ccfd74a`,
  `gpu = false` in `compat/hosts.lock.toml`) is the pure-Python/NumPy/SciPy
  electrophysiology spike-sorting library, separate from the `phy` desktop GUI.
- Admitted Windows (`compat/host-environments/phylib.import-inventory.json`) and
  Linux (`compat/host-environments/phylib-linux.import-inventory.json`,
  `docs/phylib-import-admission.md`) cells prove **import-only CPU capability**
  across all 12 `phylib.*` modules (`package_tree_sha256 ==
  3db4814e19aa3a6f9e477a7ae7a5472d1d86237b566088ecf521cbfb2e3c2a98`) with
  `loaded_vispy_modules == []`, `loaded_qt_modules == []`, and
  `rendering_qualified == false`.
- Current-wheel (`0.17.0+vulkan.2`) runs (`978`, `979`) additionally verify that
  all 12 `phylib` modules co-reside and import cleanly alongside the installed
  `vispy 0.17.0+vulkan.2` wheel in CPython 3.12 without altering `phylib`'s
  `rendering_qualified: false` classification.

### 3.4 `Visbrain` (`HOST-06`) import-only legacy constraints vs primitive smoke

- `compat/no-opengl-matrix.json` (`id: "visbrain-admission"`) records `Visbrain`
  (`0.4.5`, archive `1b5596e9e6971ffa1ef5450d297955f1d8f3c1d020050b8f4d935e3fa7276ea6`)
  as `NOT_ADMITTED`.
- Upstream `visbrain 0.4.5` (archived 2019) has three distinct boundaries that
  prevent current-wheel (`cp312` / Qt6 / no-OpenGL) host admission:
  1. **Direct OpenGL dependency**: `visbrain` declares `PyOpenGL` and imports
     `OpenGL.GL` directly in `visbrain/visuals/cbar/` and legacy visuals.
  2. **Legacy packaging & Qt5 lock-in**: `visbrain` setup/packaging relies on
     legacy `pkg_resources` / `setuptools` (`compat/host-environments/visbrain.import-failure-1.json`
     vs `compat/host-environments/visbrain.import-inventory.json` on CPython 3.11 /
     `PyQt5` where importing `visbrain` GUI/visuals loads `PyQt5.QtOpenGL`), while
     `visbrain/__init__.py` mutates `sys.excepthook` and `visbrain.objects`,
     `visbrain.visuals`, and `visbrain.gui` hardcode `from PyQt5 import ...`
     without `qtpy` (failing closed on CPython 3.12 / Qt6 with
     `ModuleNotFoundError: No module named 'PyQt5'`).
  3. **Unexecuted CPython 3.11 / PyQt5 proposal boundary**:
     `build/r01-visbrain-readiness-proposal-perf-1/proposal.json` remains
     `UNEXECUTED_PUBLIC_READINESS_PROPOSAL_ONLY_NOT_SOURCE6_ADMISSION` (requiring
     CPython 3.11.11 + `PyQt5` ABI, which current `cp312` wheels do not target).
- On current CPython 3.12 wheels (`9919a280...` and `e600b29e...`), `978` and
  `979` record:
  - the deterministic fail-closed boundary when importing unmodified
    `visbrain` (`visbrain.objects` / `visbrain.visuals` / `visbrain.gui`) in a
    clean CPython 3.12 / Qt6 environment (`ModuleNotFoundError: No module named 'PyQt5'`), and
  - a separate offscreen `SceneCanvas` + 3D `Markers` + colored `Line`
    rendered-smoke receipt exercising the underlying VisPy scenegraph primitives
    with runtime color/width mutation, RGBA readback, PNG export, and 10 zero
    live gauges, explicitly labelled
    `vispy_primitive_equivalent_only_not_visbrain_host_admission`.

## 4. Current-Wheel (`0.17.0+vulkan.2`) Renewal Receipts (2026-11-15)

- Acceptance receipt: `compat/api-acceptance/host01-06-current-wheels-v1.json`
  (`sha256=e36a08c2006d8268a2285972f3b66e08fd23bb379f6a3d3aa209cdcdab115679`)
- Windows consumer run: `D:/vispy-vulkan-managed/build/runs/gap-w2-6-windows-978`
  - Installed wheel: `9919a280a5de2c4bec45837078cb1d405e7169933ddcfb0758aa7d6a82722d39` (`537` members verified)
  - `verification.json`: `4dc8b6d504c375711506184828dca6d3fad6eefc0b59e63f86cdabcff90ea864`
  - `terminal.json`: `dfe4e38f8e912727136f70aa6868971fb4df5e5dff9c0b1eb0f7312c1813abd2`
  - `uv-cache-cleanup-note.json`: `fbe2941120ab650e16ee521452254bf3adcbf737e6daf51a342c1e78a8115b33`
  - Cleanup: `PASS_APPLY` (`deleted: 6163`, `retained_verified: 49`, scratch absent)
- WSL2 consumer run: `D:/vispy-vulkan-managed/build/runs/gap-w2-6-wsl-979`
  - Installed wheel: `e600b29e5259b896cc9d0fe36bbb5760260946aef53c013f8fc74e2fd0153007` (`537` members verified under owned `Xvfb` + pinned Mesa `9c5c41b3a7b9d759b0960c868f10375281798ad084150716d6d122c8789b9e12`)
  - `verification.json`: `d7576be24ccd16b41f1399581d33aa228cf740737ba3633ae632b3a4a2e88678`
  - `terminal.json`: `d06c9f06d6fb10381eee354fbb35b1c70a432e39480fdbaffbd6c769ad2daf09`
  - Cleanup: `PASS_APPLY` (`deleted: 5848`, `retained_verified: 78`, scratch absent on `D:/` and `/home/heq/vispy-vulkan-managed/build/work`)
