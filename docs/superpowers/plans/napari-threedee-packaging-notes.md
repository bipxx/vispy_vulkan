# Genuine pinned napari-threedee packaging and CPU registration

The exact source commit `7bd485085186ebe1907f8de931aa7a93e0d58a83` is the
upstream annotated `v0.0.29` tag. Its real tag object is
`42be31adce55bed767dd5f835c32d08c329f3e35`, which peels to that commit.
The detached checkout matched all 174 files and the complete tree digest of
the previously verified source archive. No pinned source, entry point or
manifest was patched, and no pretend-version environment override was used.

The source's declared `hatchling`/`hatch-vcs` backend generated `_version.py`
through its own VCS hook. Two builds with the commit's `SOURCE_DATE_EPOCH`
produced byte-identical `napari_threedee-0.0.29-py3-none-any.whl` files:
**102,083 bytes**, SHA256
`de115619e84a7967b0386651163c29ec12228d59e58000736067f066237ce91e`.
The generated version file is the only added source file; all original files
remain byte-identical. The wheel retains the declared real entry point
`napari-threedee = napari_threedee:napari.yaml`.

Build artifacts/logs are under
`build/host-wheels/napari-threedee-v0.0.29-qualification-{1,2}`. Exact build-tool
hashes are in
`compat/host-environments/napari-threedee-package-build-windows-cpython312.txt`.
Installed package/manifest/generated-version hashes, Git evidence, dependency
RECORD hashes, module origins, wheel contents and registration witness are
anchored by `napari-threedee-packaging-provenance.json` in the same directory.
The first probe's incorrect assumption that uv records a local wheel hash in
`direct_url.json` is retained as separate probe-failure evidence. The corrected
probe verifies the direct URL, hashed installation lock and every installed
wheel file except the installer-extended RECORD.

A fresh environment,
`build/host-environments/napari-threedee-cpython312-pyqt6-packaged`, preserves
the original CPython 3.12.8/PyQt6 6.11.0 runtime lock: 115 runtime dependencies,
two locked asciitree build tools, and the actual plugin wheel. All dependency
versions are unchanged. The 118 installed distribution RECORD hashes are
recorded separately for this environment. The previous source-copy environment
and its `unknown` version import evidence remain intact. Root `.venv`, shared
`uv.lock`, CMake and native binaries were not changed by this packet.

The real public metadata and npe2 APIs passed in a process outside the checkout:

- `importlib.metadata.entry_points(group="napari.manifest")` found the installed entry point.
- `npe2.PluginManifest.from_distribution("napari-threedee")` resolved its actual installed YAML.
- `npe2.plugin_manager.discover()` indexed the plugin and its 11 widget contributions.
- `npe2.PluginManager.commands.get()` resolved all 12 command callables from unchanged installed source.

No command was executed. No widget, viewer, QApplication, OpenGL context or
Dawn device was constructed. The plugin version is now genuinely `0.0.29`;
**graphics qualification remains pending**. Pydantic compatibility warnings
from the actual pinned environment are retained in the witness.

The executed registration command was:

```powershell
build/host-environments/napari-threedee-cpython312-pyqt6-packaged/Scripts/python.exe tools/plugin_registration.py --wheel build/host-wheels/napari-threedee-v0.0.29-qualification-1/napari_threedee-0.0.29-py3-none-any.whl --output compat/host-environments/napari-threedee-registration.json
```

Result: **11 widgets, 12 resolved commands, exit 0**. The registration/source
contracts plus preserved host-inventory contracts passed **19 tests, exit 0**.

## Public graphics and picking fixture still required

Validation owns the future fixture and capture. Use a real
`napari.Viewer(ndisplay=3)` with a fixed asymmetric 3D layer and:

```python
dock, widget = viewer.window.add_plugin_dock_widget(
    "napari-threedee", "layer manipulator"
)
widget.model.set_layers(layer)
widget.activate_button.click()
```

The registered constructor is `QtLayerManipulatorWidget(viewer)`; its model
starts disabled. Three-dimensional data and `ndisplay=3` are necessary before
activation. Public model `radius`, `handle_size` and `origin` can define fixed
analytic geometry before capture. Screenshot the actual handles/lines through
the public napari export and verify predetermined scene-transform landmarks.

Actual pinned picking uses CPU ray/sphere intersection through real
`layer.mouse_drag_callbacks`. Drive canvas Qt mouse press/move/release at
analytically projected handle centers, then verify public `layer.translate`
and model `origin`, rendered selection colors, a ray miss that preserves the
transform, and public deactivation/removal/close callback retirement. Do not
replace those events with calls to the private selection helper. This is not a
GPU ID-buffer picking implementation. The separate registered
`"render plane manipulator"` widget covers plane/rotation controls if admitted.

Relevant immutable implementation paths are
`_backend/threedee_widget_base.py`, `manipulators/layer_manipulator.py`,
`_backend/manipulator/napari_manipulator_backend.py`, and
`utils/selection_utils.py`. The backend also connects the actual canvas
QObject's `destroyed` signal to `_set_canvas_none`; installed candidate lifecycle
must be exercised. Any unchanged upstream construction, interaction, rendering
or teardown failure remains evidence of an unadmitted fixture.

## Installed candidate and a distinct NumPy-compatible pair

The installed candidate environment is
`build/host-environments/napari-threedee-cpython312-pyqt6-candidate-w5`.
It retains every upstream runtime dependency version and the genuine plugin
wheel; only VisPy is replaced by the qualified frozen-w5 CP312 wheel, SHA256
`e94ab51c4d3ad37333506af3c1b99ea3ce05cccd34bb4ea682e63ad70f2c1c3c`.
Every installed wheel file except the installer-extended RECORD was compared
against the artifact. The native module origin is inside this environment and
its SHA256 is `c3296e22d49a3f94953797b04bf8144b128cdb8e44c132d58370443120404ff9`.
The CPU registration proof again resolved 11 widgets and 12 commands, exit 0.
It imported the native ABI leaf without calling renderer entry points or
constructing an application, context or device.

Candidate provenance is
`compat/host-environments/napari-threedee-candidate-provenance-w5.json`.
The first relative-wheel-path probe failed after changing to its external
temporary directory; that exact failed record and tool source are preserved as
`napari-threedee-candidate-registration-probe-failure-1.{json,py}`. The corrected
tool resolves both wheel paths before changing directory. This CPU proof does
not admit an installed plugin graphics result.

Four public render-plane upstream attempts exposed a dependency incompatibility:
the unchanged plugin's rotator path calls `np.row_stack`, which NumPy 2.5.3
removed. Validation retains those nonzero children under
`tests/reference/napari-render-plane-opengl`. The pinned plugin declares an
unbounded NumPy dependency. A distinct pair was therefore prepared with actual
NumPy 2.4.6; the original 2.5.3 environments, locks, source and failures remain
unchanged.

The new environments are
`build/host-environments/napari-threedee-cpython312-pyqt6-{upstream,candidate}-numpy246-w5`.
They have the same 118 installed distribution versions as their corresponding
original environments except NumPy 2.4.6. Each hash lock preserves all original
requirement blocks except NumPy; the candidate retains exactly the same e94
VisPy wheel. The selected official CP312/Windows NumPy wheel SHA256 is
`d8e8286dd7cea7895157318d1b91cdacac64c479f3cbc8dce548331728484751`,
recorded in the existing immutable uv lock metadata. Both environments passed
public `row_stack` on asymmetric values, imported the unchanged public
`RenderPlaneManipulator`, resolved all 11 widgets/12 commands, and passed
`uv pip check` for all 118 packages. No QApplication or graphics device was
created. Hashes and origins are anchored in
`compat/host-environments/napari-threedee-numpy246-paired-provenance-w5.json`;
validation's primary-source dependency assessment is
`build/reports/napari-render-plane-numpy-dependency-assessment.json`.
Actual upstream capture and installed candidate parity in this pair remain
required before a render-plane fixture can be admitted.
